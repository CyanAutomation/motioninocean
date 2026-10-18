"""Tests for the OpenAPI spec and built-in API reference endpoints.

Validates that GET /openapi.json serves a valid OpenAPI spec and
GET /api/docs serves the local API reference page.
"""

import importlib
import json
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

    def test_openapi_json_public_endpoint_matches_checked_in_contract(self, monkeypatch, tmp_path):
        """The public endpoint serves the exact checked-in OpenAPI contract.

        Traceability: docs/openapi.json.
        """
        client = _new_management_client(monkeypatch, tmp_path)
        expected = json.loads((workspace_root / "docs" / "openapi.json").read_text())
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert response.mimetype == "application/json"
        actual = response.get_json()

        assert actual == expected
        assert "/api/v1/webcams" in actual["paths"]
        assert actual["info"]["title"]
        assert actual["info"]["version"]

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


class TestApiDocs:
    """Tests for the built-in API reference page."""

    def test_api_docs_is_self_contained_and_points_to_the_spec(self, monkeypatch, tmp_path):
        """Public API docs return HTML backed by loadable local assets and the OpenAPI spec."""
        client = _new_management_client(monkeypatch, tmp_path)
        response = client.get("/api/docs")
        assert response.status_code == 200
        assert response.mimetype == "text/html"
        assert b"swagger-ui" not in response.data.lower()
        assert b"unpkg.com" not in response.data.lower()
        assert b"/openapi.json" in response.data
        assert b"/static/js/api-docs.js" in response.data
        assert b"/static/css/api-docs.css" in response.data
        assert b"Motion In Ocean API" in response.data

        js_response = client.get("/static/js/api-docs.js")
        css_response = client.get("/static/css/api-docs.css")
        assert js_response.status_code == 200
        assert js_response.mimetype in {"text/javascript", "application/javascript"}
        assert js_response.data
        assert css_response.status_code == 200
        assert css_response.mimetype == "text/css"
        assert css_response.data


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
