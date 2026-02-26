"""Integration tests for the README help API endpoint."""

import importlib
import sys
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
            monkeypatch.setattr(main, "Path", path_type)
        return main.create_management_app(main._load_config()).test_client()
    finally:
        sys.path = original_sys_path


class TestReadmeHelpEndpointIntegration:
    """Integration coverage for GET /api/help/readme."""

    def test_help_readme_returns_marker_text(self, monkeypatch, tmp_path):
        """Endpoint returns README content with an expected known marker."""
        client = _new_management_client(monkeypatch, tmp_path)

        response = client.get("/api/help/readme")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data.get("content"), str)
        assert "**Motion In Ocean**" in data["content"]

    def test_help_readme_returns_404_when_readme_path_missing(self, monkeypatch, tmp_path):
        """Endpoint returns README_NOT_FOUND when path resolution points to missing README."""

        class MissingReadmePath(Path):
            """Path subclass that forces README.md to resolve to a non-existent location."""

            _flavour = type(Path())._flavour

            def __new__(cls, *args, **kwargs):
                if args and args[-1] == "README.md":
                    args = (*args[:-1], "README_DOES_NOT_EXIST_FOR_TEST.md")
                return super().__new__(cls, *args, **kwargs)

        client = _new_management_client(monkeypatch, tmp_path, path_type=MissingReadmePath)

        response = client.get("/api/help/readme")

        assert response.status_code == 404
        assert response.get_json() == {
            "error": "README_NOT_FOUND",
            "message": "README.md was not found",
        }
