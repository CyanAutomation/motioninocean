"""Integration tests for webcam control-plane auth on /api/metrics/stream."""


def _create_webcam_client(monkeypatch, tmp_path, token: str):
    """Create a webcam-mode test client with optional control-plane auth token."""
    from pi_camera_in_docker import main

    monkeypatch.setenv("MIO_APP_MODE", "webcam")
    monkeypatch.setenv("MIO_MOCK_CAMERA", "true")
    monkeypatch.setenv("MIO_NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MIO_APPLICATION_SETTINGS_PATH", str(tmp_path / "application-settings.json"))
    monkeypatch.setenv("MIO_WEBCAM_CONTROL_PLANE_AUTH_TOKEN", token)
    monkeypatch.setattr(main, "_run_webcam_mode", lambda _state, _cfg: None)

    app = main.create_webcam_app()
    return app.test_client()


def test_metrics_stream_requires_auth_when_webcam_token_configured(monkeypatch, tmp_path):
    """Without Authorization header, /api/metrics/stream should return 401 when token is set."""
    client = _create_webcam_client(monkeypatch, tmp_path, "node-shared-token")

    response = client.get("/api/metrics/stream")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_metrics_stream_opens_with_valid_bearer_when_webcam_token_configured(monkeypatch, tmp_path):
    """With valid bearer token, /api/metrics/stream should open SSE stream when token is set."""
    client = _create_webcam_client(monkeypatch, tmp_path, "node-shared-token")

    response = client.get(
        "/api/metrics/stream",
        headers={"Authorization": "Bearer node-shared-token"},
        buffered=False,
    )

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"

    first_frame = next(response.response)
    assert first_frame.startswith(b"data: ")

    response.close()


def test_metrics_stream_accessible_without_auth_when_webcam_token_unset(monkeypatch, tmp_path):
    """/api/metrics/stream should remain public when control-plane token is unset."""
    client = _create_webcam_client(monkeypatch, tmp_path, "")

    response = client.get("/api/metrics/stream", buffered=False)

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"

    first_frame = next(response.response)
    assert first_frame.startswith(b"data: ")

    response.close()
