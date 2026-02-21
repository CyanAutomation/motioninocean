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
        "webcam_control_plane_auth_token": "",
    }
    app, _limiter, state = main_module._create_base_app(cfg)
    register_shared_routes(app, state, get_stream_status=lambda: dict(stream_status_payload))
    return app, state


def test_management_endpoints_return_contract_payloads(monkeypatch, tmp_path):
    """Management mode should expose stable /health, /ready, and /metrics payload contracts."""
    from pi_camera_in_docker import main

    monkeypatch.setenv("MIO_APP_MODE", "management")
    monkeypatch.setenv("MIO_MOCK_CAMERA", "true")
    monkeypatch.setenv("MIO_NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MIO_MANAGEMENT_AUTH_TOKEN", "")

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


def test_webcam_not_ready_surfaces_camera_startup_failure_metadata():
    """Webcam /ready and /api/status should expose startup error context when camera init fails."""
    from pi_camera_in_docker import main

    app, state = _build_webcam_status_app(
        main,
        {
            "frames_captured": 0,
            "current_fps": 0.0,
            "last_frame_age_seconds": None,
        },
    )
    state["camera_startup_error"] = {
        "code": "CAMERA_UNAVAILABLE",
        "message": "No cameras detected. Check device mappings and camera hardware.",
        "reason": "camera_unavailable",
        "detection_path": "picamera2.global_camera_info",
    }
    client = app.test_client()

    ready = client.get("/ready")
    status = client.get("/api/status")

    assert ready.status_code == 503
    ready_payload = ready.get_json()
    assert ready_payload["status"] == "not_ready"
    assert ready_payload["reason"] == "camera_unavailable"
    assert ready_payload["camera_error"]["code"] == "CAMERA_UNAVAILABLE"
    assert ready_payload["camera_error"]["detection_path"] == "picamera2.global_camera_info"

    assert status.status_code == 200
    status_payload = status.get_json()
    assert status_payload["status"] == "degraded"
    assert status_payload["camera_error"]["message"].startswith("No cameras detected")


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


def test_settings_changes_reports_no_override_for_defaults(monkeypatch, tmp_path):
    """
    Verify that /api/settings/changes reports no override when persisted values
    for jpeg_quality and max_stream_connections equal effective runtime defaults.
    """
    from pi_camera_in_docker import main
    from pi_camera_in_docker.application_settings import ApplicationSettings
    from pi_camera_in_docker.runtime_config import load_env_config

    # Ensure environment variables are not set for these to pick up defaults
    monkeypatch.delenv("JPEG_QUALITY", raising=False)
    monkeypatch.delenv("MAX_STREAM_CONNECTIONS", raising=False)

    # Get the actual default values from runtime_config
    env_defaults = load_env_config()
    default_jpeg_quality = env_defaults["jpeg_quality"]
    default_max_stream_connections = env_defaults["max_stream_connections"]

    # Set up application settings path
    settings_path = tmp_path / "application-settings.json"
    monkeypatch.setenv("MIO_APPLICATION_SETTINGS_PATH", str(settings_path))
    monkeypatch.setenv("MIO_NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))

    # Create the app in management mode
    monkeypatch.setenv("APP_MODE", "management")
    app = main.create_management_app()
    client = app.test_client()

    # Persist settings with values equal to the defaults
    app_settings = ApplicationSettings(str(settings_path))
    app_settings.apply_patch_atomic(
        {
            "camera": {
                "jpeg_quality": default_jpeg_quality,
                "max_stream_connections": default_max_stream_connections,
            }
        },
        modified_by="test",
    )

    # Make a request to the /api/settings/changes endpoint
    response = client.get("/api/settings/changes")
    assert response.status_code == 200
    changes = response.get_json()

    # Assert that no overrides are reported for these settings
    overridden_settings = changes.get("overridden", [])

    # Check that 'camera.jpeg_quality' and 'camera.max_stream_connections' are NOT in the overridden list
    for override in overridden_settings:
        assert not (override["category"] == "camera" and override["key"] == "jpeg_quality")
        assert not (
            override["category"] == "camera" and override["key"] == "max_stream_connections"
        )

    # Optionally, also check that the total number of overridden settings is as expected (e.g., 0 if only these were set)
    # This might need adjustment if other settings are intentionally overridden by default in tests
    # For now, a specific check that these two are not present is sufficient.


def test_request_logging_uses_non_empty_correlation_id(monkeypatch):
    """Request logs should always include a non-empty correlation ID."""
    from pi_camera_in_docker import main

    logged_messages = []

    def _capture(level, message, *args):
        if args:
            message = message % args
        logged_messages.append((level, message))

    monkeypatch.setattr(main.logger, "log", _capture)

    app, _state = _build_webcam_status_app(
        main,
        {
            "frames_captured": 1,
            "current_fps": 1.0,
            "last_frame_age_seconds": 0.1,
        },
    )
    response = app.test_client().get("/api/status")

    assert response.status_code == 200
    request_logs = [
        message
        for _level, message in logged_messages
        if message.startswith("request correlation_id=")
    ]
    assert request_logs
    assert "correlation_id=none" not in request_logs[-1]
