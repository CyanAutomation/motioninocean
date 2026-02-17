"""
Integration tests - verify startup sequence, error recovery, and health checks.
"""

from pi_camera_in_docker.shared import register_shared_routes


def _build_webcam_status_app(main_module, stream_status_payload):
    cfg = {
        "app_mode": "webcam",
        "resolution": (640, 480),
        "fps": 0,
        "target_fps": 0,
        "jpeg_quality": 90,
        "max_frame_age_seconds": 10.0,
        "max_stream_connections": 4,
        "pi3_profile_enabled": False,
        "mock_camera": True,
        "cors_enabled": False,
        "cors_origins": "",
        "allow_pykms_mock": False,
        "webcam_registry_path": "/tmp/node-registry.json",
        "application_settings_path": "/tmp/application-settings.json",
        "management_auth_token": "",
    }
    app, _limiter, state = main_module._create_base_app(cfg)
    register_shared_routes(app, state, get_stream_status=lambda: dict(stream_status_payload))
    return app, state


def test_management_endpoints_return_contract_payloads(monkeypatch, tmp_path):
    """Management mode should expose stable /health, /ready, and /metrics payload contracts."""
    from pi_camera_in_docker import main

    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("MOCK_CAMERA", "true")
    monkeypatch.setenv("WEBCAM_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MANAGEMENT_AUTH_TOKEN", "")

    app = main.create_management_app()
    client = app.test_client()

    health = client.get("/health")
    ready = client.get("/ready")
    metrics = client.get("/metrics")

    assert health.status_code == 200
    assert health.get_json()["status"] == "healthy"
    assert health.get_json()["app_mode"] == "management"

    assert ready.status_code == 200
    assert ready.get_json()["status"] == "ready"
    assert ready.get_json()["reason"] == "no_camera_required"

    assert metrics.status_code == 200
    metrics_payload = metrics.get_json()
    assert metrics_payload["app_mode"] == "management"
    assert metrics_payload["camera_active"] is False
    assert "current_fps" in metrics_payload
    assert "frames_captured" in metrics_payload


def test_webcam_ready_transitions_from_not_ready_to_ready():
    """Webcam /ready should require recording_started and fresh stream data."""
    from pi_camera_in_docker import main

    app, state = _build_webcam_status_app(
        main,
        {
            "frames_captured": 12,
            "current_fps": 8.5,
            "last_frame_age_seconds": 0.2,
        },
    )
    client = app.test_client()

    initial = client.get("/ready")
    assert initial.status_code == 503
    assert initial.get_json()["status"] == "not_ready"

    state["recording_started"].set()
    ready = client.get("/ready")
    assert ready.status_code == 200
    ready_payload = ready.get_json()
    assert ready_payload["status"] == "ready"
    assert ready_payload["current_fps"] == 8.5
    assert ready_payload["last_frame_age_seconds"] == 0.2


def test_webcam_ready_reports_not_ready_for_stale_stream():
    """Webcam /ready should remain not_ready when latest frame age exceeds threshold."""
    from pi_camera_in_docker import main

    app, state = _build_webcam_status_app(
        main,
        {
            "frames_captured": 4,
            "current_fps": 5.0,
            "last_frame_age_seconds": 12.0,
        },
    )
    state["recording_started"].set()
    client = app.test_client()

    response = client.get("/ready")
    assert response.status_code == 503
    payload = response.get_json()
    assert payload["status"] == "not_ready"
    assert payload["last_frame_age_seconds"] == 12.0


def test_webcam_metrics_and_status_reflect_stream_activity():
    """Webcam /metrics and /api/status should map recording/freshness to semantic status fields."""
    from pi_camera_in_docker import main

    app, state = _build_webcam_status_app(
        main,
        {
            "frames_captured": 21,
            "current_fps": 14.0,
            "last_frame_age_seconds": 0.4,
        },
    )
    state["recording_started"].set()
    client = app.test_client()

    metrics = client.get("/metrics")
    status = client.get("/api/status")

    assert metrics.status_code == 200
    metrics_payload = metrics.get_json()
    assert metrics_payload["camera_mode_enabled"] is True
    assert metrics_payload["camera_active"] is True
    assert metrics_payload["frames_captured"] == 21
    assert metrics_payload["current_fps"] == 14.0

    assert status.status_code == 200
    status_payload = status.get_json()
    assert status_payload["status"] == "ok"
    assert status_payload["stream_available"] is True
    assert status_payload["camera_active"] is True
    assert status_payload["fps"] == 14.0


def test_shared_health_endpoints_exist():
    """Verify shared /health and /ready endpoints are registered in the Flask app's URL map."""
    from pi_camera_in_docker import main

    cfg = main._load_config()
    cfg["mock_camera"] = True
    app = main.create_webcam_app(cfg)  # Use webcam app as it has all shared routes

    # Check for /health and /ready
    assert "/health" in [str(rule) for rule in app.url_map.iter_rules()]
    assert "/ready" in [str(rule) for rule in app.url_map.iter_rules()]


def test_shared_metrics_endpoint_exists():
    """Verify shared /metrics endpoint is registered in the Flask app's URL map."""
    from pi_camera_in_docker import main

    cfg = main._load_config()
    cfg["mock_camera"] = True
    app = main.create_webcam_app(cfg)  # Use webcam app as it has all shared routes

    # Check for /metrics
    assert "/metrics" in [str(rule) for rule in app.url_map.iter_rules()]
