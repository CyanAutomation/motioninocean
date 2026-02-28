"""Tests for OpenAPI spec and Swagger UI endpoints.

Validates that GET /openapi.json serves a valid OpenAPI spec and
GET /api/docs serves the Swagger UI HTML page.
"""

import importlib
import sys
from pathlib import Path


workspace_root = Path(__file__).parent.parent


def _new_management_client(monkeypatch, tmp_path, management_token="test-token"):
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
        return main.create_management_app(main._load_config()).test_client()
    finally:
        sys.path = original_sys_path


class TestOpenAPISpec:
    """Tests for GET /openapi.json."""

    def test_openapi_json_returns_200(self, monkeypatch, tmp_path):
        """GET /openapi.json returns HTTP 200."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_openapi_json_content_type(self, monkeypatch, tmp_path):
        """GET /openapi.json returns application/json content type."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.get("/openapi.json")
        assert "application/json" in response.content_type

    def test_openapi_json_has_required_top_level_keys(self, monkeypatch, tmp_path):
        """GET /openapi.json response conforms to OpenAPI 3.0 schema."""
        client = _new_management_client(monkeypatch, tmp_path)
        data = client.get("/openapi.json").get_json()

        # Check required keys and basic structure
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

        # Validate info structure
        assert isinstance(data["info"], dict)
        assert "title" in data["info"]
        assert "version" in data["info"]
        assert isinstance(data["info"]["title"], str)
        assert isinstance(data["info"]["version"], str)

        # Validate paths is non-empty dict
        assert isinstance(data["paths"], dict)
        assert len(data["paths"]) > 0

        # Validate OpenAPI version is 3.x
        assert data["openapi"].startswith("3.")

    def test_openapi_json_info_has_title_and_version(self, monkeypatch, tmp_path):
        """GET /openapi.json info block includes title and version."""
        client = _new_management_client(monkeypatch, tmp_path)
        info = client.get("/openapi.json").get_json()["info"]
        assert "title" in info
        assert "version" in info
        assert info["title"]  # non-empty
        assert info["version"]  # non-empty

    def test_openapi_json_paths_includes_webcams(self, monkeypatch, tmp_path):
        """GET /openapi.json paths block includes /api/v1/webcams."""
        client = _new_management_client(monkeypatch, tmp_path)
        paths = client.get("/openapi.json").get_json()["paths"]
        assert any("webcams" in path for path in paths)

    def test_openapi_json_unauthenticated(self, monkeypatch, tmp_path):
        """GET /openapi.json is publicly accessible without auth token."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.get("/openapi.json")  # no Authorization header
        assert response.status_code == 200

    def test_openapi_metrics_snapshot_excludes_resolution(self, monkeypatch, tmp_path):
        """MetricsSnapshot schema omits resolution to match /metrics payload contract."""
        client = _new_management_client(monkeypatch, tmp_path)
        schema = client.get("/openapi.json").get_json()["components"]["schemas"]["MetricsSnapshot"]
        properties = schema.get("properties", {})

        assert "resolution" not in properties
        assert {
            "app_mode",
            "camera_mode_enabled",
            "camera_active",
            "uptime_seconds",
            "max_frame_age_seconds",
            "frames_captured",
            "current_fps",
            "last_frame_age_seconds",
            "timestamp",
        }.issuperset(properties.keys())


class TestSwaggerUI:
    """Tests for GET /api/docs (Swagger UI)."""

    def test_api_docs_returns_200(self, monkeypatch, tmp_path):
        """GET /api/docs returns HTTP 200."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.get("/api/docs")
        assert response.status_code == 200

    def test_api_docs_content_type_is_html(self, monkeypatch, tmp_path):
        """GET /api/docs returns text/html content type."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.get("/api/docs")
        assert "text/html" in response.content_type

    def test_api_docs_contains_swagger_ui(self, monkeypatch, tmp_path):
        """GET /api/docs HTML references swagger-ui."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.get("/api/docs")
        assert b"swagger-ui" in response.data.lower()

    def test_api_docs_points_to_openapi_json(self, monkeypatch, tmp_path):
        """GET /api/docs HTML references /openapi.json as the spec URL."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.get("/api/docs")
        assert b"/openapi.json" in response.data

    def test_api_docs_unauthenticated(self, monkeypatch, tmp_path):
        """GET /api/docs is publicly accessible without auth token."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.get("/api/docs")  # no Authorization header
        assert response.status_code == 200


class TestReadmeHelpEndpoint:
    """Tests for GET /api/help/readme."""

    def test_readme_help_returns_200(self, monkeypatch, tmp_path):
        """GET /api/help/readme returns HTTP 200."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.get("/api/help/readme")
        assert response.status_code == 200

    def test_readme_help_returns_json_with_content(self, monkeypatch, tmp_path):
        """GET /api/help/readme returns content in JSON payload."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.get("/api/help/readme")
        data = response.get_json()
        assert "application/json" in response.content_type
        assert isinstance(data.get("content"), str)
        assert len(data["content"]) > 0

    def test_readme_help_unauthenticated(self, monkeypatch, tmp_path):
        """GET /api/help/readme is publicly accessible without auth token."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.get("/api/help/readme")
        assert response.status_code == 200


class TestDeprecatedAliases:
    """Tests for 308 redirect aliases covering pre-v1 /api/* paths."""

    def test_deprecated_webcams_list_returns_308(self, monkeypatch, tmp_path):
        """GET /api/webcams redirects with 308 to /api/v1/webcams."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.get("/api/webcams", headers={"Authorization": "Bearer test-token"})
        assert response.status_code == 308
        assert response.headers.get("Location", "").endswith("/api/v1/webcams")

    def test_deprecated_webcams_redirect_has_deprecation_header(self, monkeypatch, tmp_path):
        """308 redirect for /api/webcams includes Deprecation: true header."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.get("/api/webcams", headers={"Authorization": "Bearer test-token"})
        assert response.headers.get("Deprecation") == "true"

    def test_deprecated_management_overview_returns_308(self, monkeypatch, tmp_path):
        """GET /api/management/overview redirects with 308."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.get(
            "/api/management/overview",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 308
        assert "/api/v1/management/overview" in response.headers.get("Location", "")

    def test_deprecated_settings_returns_308(self, monkeypatch, tmp_path):
        """GET /api/settings redirects with 308 to /api/v1/settings."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.get("/api/settings", headers={"Authorization": "Bearer test-token"})
        assert response.status_code == 308
        assert "/api/v1/settings" in response.headers.get("Location", "")

    def test_deprecated_discovery_announce_returns_308(self, monkeypatch, tmp_path):
        """POST /api/discovery/announce redirects with 308."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.post(
            "/api/discovery/announce",
            json={"name": "test"},
            headers={"Authorization": "Bearer discovery-secret"},
        )
        assert response.status_code == 308
        assert "/api/v1/discovery/announce" in response.headers.get("Location", "")
