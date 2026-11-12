"""Integration tests for the public demo's read-only behavior."""

import importlib
import sys
from pathlib import Path

import pytest


workspace_root = Path(__file__).resolve().parents[2]


@pytest.fixture
def demo_app(monkeypatch, tmp_path):
    """Create a webcam app with mock frames and the demo read-only policy."""
    settings_path = tmp_path / "application-settings.json"
    monkeypatch.setenv("MIO_APPLICATION_SETTINGS_PATH", str(settings_path))
    monkeypatch.setenv("MIO_APP_MODE", "webcam")
    monkeypatch.setenv("MIO_MOCK_CAMERA", "true")
    monkeypatch.setenv("MIO_DEMO_READ_ONLY", "true")
    monkeypatch.setenv("MIO_WEBCAM_CONTROL_PLANE_AUTH_TOKEN", "")

    original_sys_path = sys.path.copy()
    sys.path.insert(0, str(workspace_root))
    try:
        sys.modules.pop("pi_camera_in_docker.feature_flags", None)
        sys.modules.pop("pi_camera_in_docker.main", None)
        main = importlib.import_module("pi_camera_in_docker.main")
        app = main.create_webcam_app(main._load_config())
        yield app, settings_path
        main._shutdown_camera(app.motion_state)
    finally:
        sys.path = original_sys_path


def test_public_demo_keeps_viewer_and_read_only_views_available(demo_app):
    """The viewer and safe GET endpoints remain usable in read-only mode."""
    app, _settings_path = demo_app
    client = app.test_client()

    page = client.get("/")
    settings = client.get("/api/v1/settings")
    status = client.get("/api/status")

    assert page.status_code == 200
    assert b"Public demo" in page.data
    assert b"Read-only" in page.data
    assert b'id="config-tab-btn"' in page.data
    assert b'id="settings-tab-btn"' not in page.data
    assert b'id="setup-tab-btn"' not in page.data
    assert b'id="mobile-settings-tab-btn"' not in page.data
    assert b'id="mobile-setup-tab-btn"' not in page.data
    assert settings.status_code == 200
    assert status.status_code == 200


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("patch", "/api/v1/settings", {"camera": {"fps": 3}}),
        ("put", "/api/v1/settings", {"camera": {"fps": 3}}),
        ("delete", "/api/v1/settings", None),
        ("post", "/api/v1/settings/reset", None),
        ("post", "/api/actions/stream/start", None),
        ("post", "/api/setup/generate", {"app_mode": "webcam"}),
    ],
)
def test_public_demo_blocks_all_mutating_requests(demo_app, method, path, payload):
    """Write endpoints reject unauthenticated mutations before doing work."""
    app, settings_path = demo_app
    client = app.test_client()

    response = getattr(client, method)(path, json=payload)

    assert response.status_code == 403
    assert response.get_json()["error"] == "DEMO_READ_ONLY"
    assert not settings_path.exists()


def test_options_remains_available_for_safe_preflight_requests(demo_app):
    """HTTP preflight requests remain safe and are not mistaken for writes."""
    app, _settings_path = demo_app

    response = app.test_client().options("/api/v1/settings")

    assert response.status_code == 200
