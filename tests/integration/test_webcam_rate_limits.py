"""Integration tests for webcam-mode request rate limits."""

import importlib
import sys
from pathlib import Path


workspace_root = Path(__file__).resolve().parents[2]


def _new_webcam_client(monkeypatch, tmp_path):
    """Create a fresh webcam-mode Flask test client with mock camera enabled."""
    monkeypatch.setenv("MIO_APPLICATION_SETTINGS_PATH", str(tmp_path / "application-settings.json"))
    monkeypatch.setenv("MIO_APP_MODE", "webcam")
    monkeypatch.setenv("MIO_MOCK_CAMERA", "true")
    monkeypatch.setenv("MIO_MAX_STREAM_CONNECTIONS", "1000")
    monkeypatch.setenv("MIO_WEBCAM_CONTROL_PLANE_AUTH_TOKEN", "")

    original_sys_path = sys.path.copy()
    sys.path.insert(0, str(workspace_root))
    try:
        sys.modules.pop("pi_camera_in_docker.main", None)
        main = importlib.import_module("pi_camera_in_docker.main")
        return main.create_webcam_app(main._load_config()).test_client()
    finally:
        sys.path = original_sys_path


class TestWebcamRouteRateLimitsIntegration:
    """Verify expensive webcam paths return 429 when rate thresholds are exceeded."""

    def test_snapshot_jpg_returns_429_after_rate_threshold(self, monkeypatch, tmp_path):
        """/snapshot.jpg enforces configured burst+sustained request limits."""
        client = _new_webcam_client(monkeypatch, tmp_path)

        for _ in range(10):
            response = client.get("/snapshot.jpg")
            assert response.status_code != 429

        limited = client.get("/snapshot.jpg")
        assert limited.status_code == 429

    def test_webcam_snapshot_query_returns_429_after_rate_threshold(self, monkeypatch, tmp_path):
        """/webcam?action=snapshot enforces snapshot-specific request limits."""
        client = _new_webcam_client(monkeypatch, tmp_path)

        for _ in range(10):
            response = client.get("/webcam?action=snapshot")
            assert response.status_code != 429

        limited = client.get("/webcam?action=snapshot")
        assert limited.status_code == 429

    def test_snapshot_like_action_returns_429_after_rate_threshold(self, monkeypatch, tmp_path):
        """/api/actions/snapshot uses stricter snapshot-like action limits."""
        client = _new_webcam_client(monkeypatch, tmp_path)

        for _ in range(10):
            response = client.post("/api/actions/snapshot", json={})
            assert response.status_code != 429

        limited = client.post("/api/actions/snapshot", json={})
        assert limited.status_code == 429

    def test_stream_mjpg_returns_429_after_reconnect_churn(self, monkeypatch, tmp_path):
        """/stream.mjpg applies request-rate throttling for repeated reconnect churn."""
        client = _new_webcam_client(monkeypatch, tmp_path)

        for _ in range(10):
            response = client.get("/stream.mjpg")
            response.close()
            assert response.status_code != 429

        limited = client.get("/stream.mjpg")
        limited.close()
        assert limited.status_code == 429
