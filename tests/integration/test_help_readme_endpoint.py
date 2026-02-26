"""Integration tests for the README help API endpoint."""

import importlib
import sys
import urllib.error
from pathlib import Path


workspace_root = Path(__file__).resolve().parents[2]


def _new_management_client(monkeypatch, tmp_path, management_token="test-token", path_type=None):
    """Create a fresh management-mode Flask test client."""
    monkeypatch.setenv(
        "MIO_APPLICATION_SETTINGS_PATH",
        str(tmp_path / "application-settings.json"),
    )
    monkeypatch.setenv("MIO_APP_MODE", "management")
    monkeypatch.setenv("MIO_NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MIO_MANAGEMENT_AUTH_TOKEN", management_token)
    monkeypatch.setenv("MIO_NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")

    original_sys_path = sys.path.copy()
    sys.path.insert(0, str(workspace_root))
    try:
        sys.modules.pop("pi_camera_in_docker.main", None)
        sys.modules.pop("pi_camera_in_docker.management_api", None)
        main = importlib.import_module("pi_camera_in_docker.main")
        if path_type is not None:
            # Create a fake non-existent path
            fake_path = path_type(__file__).parent / "README_DOES_NOT_EXIST_FOR_TEST.md"
            monkeypatch.setattr(main, "_readme_path", fake_path)
        return main.create_management_app(main._load_config()).test_client()
    finally:
        sys.path = original_sys_path


class TestReadmeHelpEndpointIntegration:
    """Integration coverage for GET /api/help/readme."""

    def test_help_readme_returns_local_content_when_available(self, monkeypatch, tmp_path):
        """Endpoint returns local README content when file exists."""
        client = _new_management_client(monkeypatch, tmp_path)

        response = client.get("/api/help/readme")

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "ok"
        assert payload["source"] == "local"
        assert isinstance(payload["content"], str)
        assert "Motion In Ocean" in payload["content"]

    def test_help_readme_returns_remote_content_when_local_missing(self, monkeypatch, tmp_path):
        """Endpoint returns remote README content when local file is unavailable."""

        class MissingReadmePath(Path):
            """Path subclass that forces README.md to resolve to a non-existent location."""

            _flavour = type(Path())._flavour

            def __new__(cls, *args, **kwargs):
                if args and args[-1] == "README.md":
                    args = (*args[:-1], "README_DOES_NOT_EXIST_FOR_TEST.md")
                return super().__new__(cls, *args, **kwargs)

        client = _new_management_client(monkeypatch, tmp_path, path_type=MissingReadmePath)
        from pi_camera_in_docker import main

        class _MockHeaders:
            def get_content_charset(self, default):
                return default

        class _MockResponse:
            headers = _MockHeaders()

            def read(self):
                return b"# Remote README\n"

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        monkeypatch.setattr(
            main.urllib.request, "urlopen", lambda *_args, **_kwargs: _MockResponse()
        )

        response = client.get("/api/help/readme")

        assert response.status_code == 200
        assert response.get_json() == {
            "status": "ok",
            "content": "# Remote README\n",
            "source": "remote",
        }

    def test_help_readme_returns_degraded_payload_when_all_sources_unavailable(
        self, monkeypatch, tmp_path
    ):
        """Endpoint returns degraded payload when local and remote README sources are unavailable."""

        class MissingReadmePath(Path):
            """Path subclass that forces README.md to resolve to a non-existent location."""

            _flavour = type(Path())._flavour

            def __new__(cls, *args, **kwargs):
                if args and args[-1] == "README.md":
                    args = (*args[:-1], "README_DOES_NOT_EXIST_FOR_TEST.md")
                return super().__new__(cls, *args, **kwargs)

        client = _new_management_client(monkeypatch, tmp_path, path_type=MissingReadmePath)
        from pi_camera_in_docker import main

        def _raise_url_error(*_args, **_kwargs):
            raise urllib.error.URLError("network unavailable")

        monkeypatch.setattr(main.urllib.request, "urlopen", _raise_url_error)

        response = client.get("/api/help/readme")

        assert response.status_code == 200
        assert response.get_json() == {
            "status": "degraded",
            "content": None,
            "documentation_url": "https://github.com/CyanAutomation/motioninocean#readme",
            "message": "README content is currently unavailable. Visit the documentation URL for guidance.",
            "source": "fallback_link",
        }
