"""Integration tests for /api/metrics/stream webcam control-plane auth behavior."""

import importlib
import sys
from pathlib import Path


workspace_root = Path(__file__).resolve().parents[2]


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


def test_metrics_stream_requires_auth_when_webcam_token_configured(monkeypatch, tmp_path):
    """/api/metrics/stream returns 401 without auth header when token is configured."""
    client = _new_webcam_client(monkeypatch, tmp_path, webcam_token="webcam-token")

    response = client.get("/api/metrics/stream")

    assert response.status_code == 401


def test_metrics_stream_opens_with_valid_bearer_when_webcam_token_configured(monkeypatch, tmp_path):
    """/api/metrics/stream opens when valid bearer token is provided."""
    client = _new_webcam_client(monkeypatch, tmp_path, webcam_token="webcam-token")

    response = client.get(
        "/api/metrics/stream",
        headers={"Authorization": "Bearer webcam-token"},
        buffered=False,
    )

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    first_chunk = next(response.response).decode("utf-8")
    assert first_chunk.startswith("data: ")
    response.close()


def test_metrics_stream_is_accessible_when_webcam_token_not_configured(monkeypatch, tmp_path):
    """/api/metrics/stream remains public when webcam token is not configured."""
    client = _new_webcam_client(monkeypatch, tmp_path, webcam_token="")

    response = client.get("/api/metrics/stream", buffered=False)

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    first_chunk = next(response.response).decode("utf-8")
    assert first_chunk.startswith("data: ")
    response.close()
