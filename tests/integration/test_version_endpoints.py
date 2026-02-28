"""Integration tests for shared version endpoints."""

import importlib
import sys
from pathlib import Path


workspace_root = Path(__file__).resolve().parents[2]


def _new_management_client(monkeypatch, tmp_path, management_token=""):
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
        main = importlib.import_module("pi_camera_in_docker.main")
        return main.create_management_app(main._load_config()).test_client()
    finally:
        sys.path = original_sys_path


def _new_webcam_client(monkeypatch, tmp_path, webcam_token=""):
    """Create a fresh webcam-mode Flask test client."""
    monkeypatch.setenv(
        "MIO_APPLICATION_SETTINGS_PATH",
        str(tmp_path / "application-settings.json"),
    )
    monkeypatch.setenv("MIO_APP_MODE", "webcam")
    monkeypatch.setenv("MIO_WEBCAM_CONTROL_PLANE_AUTH_TOKEN", webcam_token)
    monkeypatch.setenv("MOCK_CAMERA", "true")

    original_sys_path = sys.path.copy()
    sys.path.insert(0, str(workspace_root))
    try:
        sys.modules.pop("pi_camera_in_docker.main", None)
        main = importlib.import_module("pi_camera_in_docker.main")
        return main.create_webcam_app(main._load_config()).test_client()
    finally:
        sys.path = original_sys_path


def _assert_version_payload_shape(payload: dict) -> None:
    """Assert required version payload contract."""
    assert payload["status"] == "ok"
    assert isinstance(payload["version"], str)
    assert isinstance(payload["source"], str)
    assert payload["app_mode"] in {"webcam", "management"}
    assert isinstance(payload["timestamp"], str)


def test_management_version_endpoints_return_same_payload_shape(monkeypatch, tmp_path):
    """Both version aliases return 200 and equivalent payload structure."""
    client = _new_management_client(monkeypatch, tmp_path, management_token="management-token")

    response_primary = client.get("/version")
    response_alias = client.get("/api/version")

    assert response_primary.status_code == 200
    assert response_alias.status_code == 200

    payload_primary = response_primary.get_json()
    payload_alias = response_alias.get_json()
    _assert_version_payload_shape(payload_primary)
    _assert_version_payload_shape(payload_alias)

    # Timestamps may differ by milliseconds; compare stable fields.
    comparable_keys = {"status", "version", "source", "app_mode"}
    assert {k: payload_primary[k] for k in comparable_keys} == {
        k: payload_alias[k] for k in comparable_keys
    }


def test_version_endpoints_fallback_to_unknown_when_no_version_file(monkeypatch, tmp_path):
    """Version endpoints return unknown fallback when VERSION file is unavailable."""
    client = _new_management_client(monkeypatch, tmp_path)

    from pi_camera_in_docker import version_info

    monkeypatch.setattr(
        version_info,
        "VERSION_FILE_CANDIDATES",
        (tmp_path / "MISSING_VERSION_FILE",),
    )

    response = client.get("/version")

    assert response.status_code == 200
    payload = response.get_json()
    _assert_version_payload_shape(payload)
    assert payload["version"] == "unknown"
    assert payload["source"] == "unknown"


def test_version_endpoints_require_webcam_control_plane_token_when_configured(
    monkeypatch, tmp_path
):
    """Version endpoints are protected in webcam mode when token is configured."""
    client = _new_webcam_client(monkeypatch, tmp_path, webcam_token="webcam-token")

    unauthorized_primary = client.get("/version")
    unauthorized_alias = client.get("/api/version")

    assert unauthorized_primary.status_code == 401
    assert unauthorized_alias.status_code == 401

    headers = {"Authorization": "Bearer webcam-token"}
    authorized_primary = client.get("/version", headers=headers)
    authorized_alias = client.get("/api/version", headers=headers)

    assert authorized_primary.status_code == 200
    assert authorized_alias.status_code == 200
    _assert_version_payload_shape(authorized_primary.get_json())
    _assert_version_payload_shape(authorized_alias.get_json())
