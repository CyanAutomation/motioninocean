import importlib
import sys
import tempfile
import time
from pathlib import Path

from flask import Flask

from pi_camera_in_docker.application_settings import ApplicationSettings

# Add workspace root to sys.path for proper package imports
workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root))


def test_management_mode_boots_without_camera(monkeypatch):
    # Set NODE_REGISTRY_PATH to a temp directory to avoid permission issues
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("NODE_REGISTRY_PATH", f"{tmpdir}/registry.json")
        monkeypatch.setenv("APP_MODE", "management")
        monkeypatch.setenv("MOTION_IN_OCEAN_MOCK_CAMERA", "false")

        sys.modules.pop("pi_camera_in_docker.main", None)
        sys.modules.pop("picamera2", None)

        main = importlib.import_module("pi_camera_in_docker.main")
        client = main.create_management_app(main._load_config()).test_client()

        health = client.get("/health")
        assert health.status_code == 200
        assert health.json["app_mode"] == "management"

        ready = client.get("/ready")
        assert ready.status_code == 200
        assert ready.json["reason"] == "no_camera_required"

        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert metrics.json["camera_mode_enabled"] is False

        status = client.get("/api/status")
        assert status.status_code == 200
        assert status.json["status"] == "ok"
        assert status.json["app_mode"] == "management"
        assert status.json["stream_available"] is False
        assert status.json["camera_active"] is False
        assert status.json["fps"] == 0.0
        assert status.json["connections"] == {"current": 0, "max": 0}

        stream = client.get("/stream.mjpg")
        assert stream.status_code == 404

        snapshot = client.get("/snapshot.jpg")
        assert snapshot.status_code == 404

        assert "picamera2" not in sys.modules


def test_webcam_mode_env_validation_and_startup(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("NODE_REGISTRY_PATH", f"{tmpdir}/registry.json")
        monkeypatch.setenv("APP_MODE", "management")
        monkeypatch.setenv("MOCK_CAMERA", "true")
        monkeypatch.setenv("RESOLUTION", "0x5000")
        monkeypatch.setenv("FPS", "bad")
        monkeypatch.setenv("TARGET_FPS", "also_bad")
        monkeypatch.setenv("JPEG_QUALITY", "1000")
        monkeypatch.setenv("MAX_FRAME_AGE_SECONDS", "-1")
        monkeypatch.setenv("MAX_STREAM_CONNECTIONS", "not_an_int")

        sys.modules.pop("pi_camera_in_docker.main", None)
        main = importlib.import_module("pi_camera_in_docker.main")

        cfg = main._load_config()
        assert cfg["resolution"] == (640, 480)
        assert cfg["fps"] == 0
        assert cfg["target_fps"] == 0
        assert cfg["jpeg_quality"] == 90
        assert cfg["max_frame_age_seconds"] == 10.0
        assert cfg["max_stream_connections"] == 10

        cfg["app_mode"] = "webcam"
        cfg["mock_camera"] = True
        app = main.create_webcam_app(cfg)
        ready = app.test_client().get("/ready")
        assert ready.status_code in (200, 503)


def test_root_serves_management_template_in_management_mode(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("NODE_REGISTRY_PATH", f"{tmpdir}/registry.json")
        monkeypatch.setenv("APP_MODE", "management")

        sys.modules.pop("pi_camera_in_docker.main", None)
        main = importlib.import_module("pi_camera_in_docker.main")
        client = main.create_management_app(main._load_config()).test_client()

        response = client.get("/")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Node Management" in html
        assert "/static/js/management.js" in html


def test_root_serves_stream_template_in_webcam_mode(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("NODE_REGISTRY_PATH", f"{tmpdir}/registry.json")
        monkeypatch.setenv("APP_MODE", "management")
        monkeypatch.setenv("MOCK_CAMERA", "true")

        sys.modules.pop("pi_camera_in_docker.main", None)
        main = importlib.import_module("pi_camera_in_docker.main")
        cfg = main._load_config()
        cfg["app_mode"] = "webcam"
        cfg["mock_camera"] = True
        app = main.create_webcam_app(cfg)
        client = app.test_client()

        response = client.get("/")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "motion-in-ocean - Camera Stream" in html
        assert "/static/js/app.js" in html


def test_api_config_returns_render_config_shape_in_management_mode(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("NODE_REGISTRY_PATH", f"{tmpdir}/registry.json")
        monkeypatch.setenv("APP_MODE", "management")
        monkeypatch.setenv("MOTION_IN_OCEAN_CORS_ORIGINS", "https://example.test")
        monkeypatch.setenv("MOCK_CAMERA", "false")
        monkeypatch.setenv("MOTION_IN_OCEAN_MOCK_CAMERA", "false")

        sys.modules.pop("pi_camera_in_docker.main", None)
        main = importlib.import_module("pi_camera_in_docker.main")
        app = main.create_management_app(main._load_config())
        client = app.test_client()

        response = client.get("/api/config")
        assert response.status_code == 200
        body = response.get_json()

        assert body["camera_settings"] == {
            "resolution": [640, 480],
            "fps": 0,
            "target_fps": 0,
            "jpeg_quality": 90,
        }
        assert body["stream_control"]["max_stream_connections"] == 10
        assert body["stream_control"]["current_stream_connections"] == 0
        assert body["stream_control"]["max_frame_age_seconds"] == 10.0
        assert body["stream_control"]["cors_origins"] == "https://example.test"

        assert body["runtime"]["camera_active"] is False
        assert isinstance(body["runtime"]["mock_camera"], bool)
        assert body["runtime"]["uptime_seconds"] is None
        _assert_health_check_contract(body)
        assert body["health_check"]["camera_pipeline"]["state"] == "unknown"
        assert body["health_check"]["stream_freshness"]["state"] == "unknown"
        assert body["health_check"]["connection_capacity"]["state"] == "ok"
        assert body["health_check"]["mock_mode"]["state"] in {"ok", "warn"}
        assert "limits" not in body

        assert isinstance(body["timestamp"], str)
        assert body["app_mode"] == "management"


def test_api_config_returns_webcam_connection_counts(monkeypatch):
    client = _new_webcam_client(monkeypatch, "")
    response = client.get("/api/config")

    assert response.status_code == 200
    body = response.get_json()
    assert body["app_mode"] == "webcam"
    assert body["stream_control"]["max_stream_connections"] == 10
    assert body["stream_control"]["current_stream_connections"] == 0
    _assert_health_check_contract(body)
    assert body["health_check"]["camera_pipeline"]["state"] in {"ok", "fail"}
    assert body["health_check"]["stream_freshness"]["state"] in {"ok", "fail", "unknown"}
    assert body["health_check"]["connection_capacity"]["state"] in {"ok", "warn", "fail"}
    assert body["health_check"]["mock_mode"]["state"] in {"ok", "warn"}


def test_api_config_webcam_includes_render_config_keys_and_defaulted_values(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("NODE_REGISTRY_PATH", f"{tmpdir}/registry.json")
        monkeypatch.setenv("APP_MODE", "management")
        monkeypatch.setenv("MOCK_CAMERA", "true")
        monkeypatch.setenv("RESOLUTION", "invalid")
        monkeypatch.setenv("FPS", "invalid")
        monkeypatch.setenv("TARGET_FPS", "invalid")
        monkeypatch.setenv("JPEG_QUALITY", "1000")
        monkeypatch.setenv("MAX_STREAM_CONNECTIONS", "invalid")
        monkeypatch.setenv("MAX_FRAME_AGE_SECONDS", "invalid")
        monkeypatch.setenv("MOTION_IN_OCEAN_CORS_ORIGINS", "")

        sys.modules.pop("pi_camera_in_docker.main", None)
        main = importlib.import_module("pi_camera_in_docker.main")
        cfg = main._load_config()
        cfg["app_mode"] = "webcam"
        cfg["mock_camera"] = True
        client = main.create_webcam_app(cfg).test_client()

        response = client.get("/api/config")
        assert response.status_code == 200
        body = response.get_json()

        _assert_render_config_contract(body)
        assert body["camera_settings"] == {
            "resolution": [640, 480],
            "fps": 0,
            "target_fps": 0,
            "jpeg_quality": 90,
        }
        assert body["stream_control"]["max_stream_connections"] == 10
        assert body["stream_control"]["max_frame_age_seconds"] == 10.0
        assert body["stream_control"]["cors_origins"] == "*"
        assert isinstance(body["runtime"]["uptime_seconds"], float)
        assert body["runtime"]["uptime_seconds"] >= 0.0
        _assert_health_check_contract(body)


def test_api_config_management_includes_render_config_keys_and_defaulted_values(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("NODE_REGISTRY_PATH", f"{tmpdir}/registry.json")
        monkeypatch.setenv("APP_MODE", "management")
        monkeypatch.setenv("MOTION_IN_OCEAN_MOCK_CAMERA", "false")
        monkeypatch.setenv("RESOLUTION", "invalid")
        monkeypatch.setenv("FPS", "invalid")
        monkeypatch.setenv("TARGET_FPS", "invalid")
        monkeypatch.setenv("JPEG_QUALITY", "1000")
        monkeypatch.setenv("MAX_STREAM_CONNECTIONS", "invalid")
        monkeypatch.setenv("MAX_FRAME_AGE_SECONDS", "invalid")
        monkeypatch.setenv("MOTION_IN_OCEAN_CORS_ORIGINS", "")

        sys.modules.pop("pi_camera_in_docker.main", None)
        main = importlib.import_module("pi_camera_in_docker.main")
        client = main.create_management_app(main._load_config()).test_client()

        response = client.get("/api/config")
        assert response.status_code == 200
        body = response.get_json()

        _assert_render_config_contract(body)
        assert body["camera_settings"] == {
            "resolution": [640, 480],
            "fps": 0,
            "target_fps": 0,
            "jpeg_quality": 90,
        }
        assert body["stream_control"]["max_stream_connections"] == 10
        assert body["stream_control"]["current_stream_connections"] == 0
        assert body["stream_control"]["max_frame_age_seconds"] == 10.0
        assert body["stream_control"]["cors_origins"] == "*"
        assert body["runtime"]["camera_active"] is False
        assert body["runtime"]["uptime_seconds"] is None
        _assert_health_check_contract(body)


def test_request_logging_levels(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("NODE_REGISTRY_PATH", f"{tmpdir}/registry.json")
        monkeypatch.setenv("APP_MODE", "management")

        sys.modules.pop("pi_camera_in_docker.main", None)
        main = importlib.import_module("pi_camera_in_docker.main")
        client = main.create_management_app(main._load_config()).test_client()

        records = []

        def capture(level, msg, *args, **kwargs):
            records.append((level, msg % args))

        monkeypatch.setattr(main.logger, "log", capture)

        health = client.get("/health")
        metrics = client.get("/metrics")

        assert health.status_code == 200
        assert metrics.status_code == 200

        health_record = next((message for _, message in records if "path=/health" in message), None)
        metrics_record = next(
            (message for _, message in records if "path=/metrics" in message), None
        )
        health_level = next(
            (level for level, message in records if "path=/health" in message), None
        )
        metrics_level = next(
            (level for level, message in records if "path=/metrics" in message), None
        )

        assert health_record is not None, "No health endpoint log found"
        assert metrics_record is not None, "No metrics endpoint log found"
        assert health_level is not None, "No health level log found"
        assert metrics_level is not None, "No metrics level log found"

    assert "method=GET path=/health status=200 latency_ms=" in health_record
    assert "method=GET path=/metrics status=200 latency_ms=" in metrics_record
    assert health_level == main.logging.DEBUG
    assert metrics_level == main.logging.INFO


def _new_webcam_client(monkeypatch, token: str):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("NODE_REGISTRY_PATH", f"{tmpdir}/registry.json")
    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("MOCK_CAMERA", "true")
    monkeypatch.setenv("MANAGEMENT_AUTH_TOKEN", token)

    # Monkeypatch ApplicationSettings to use tmpdir
    from pi_camera_in_docker.application_settings import ApplicationSettings
    original_app_settings_init = ApplicationSettings.__init__

    def mock_app_settings_init(self, path=None):
        if path is None:
            path = str(Path(tmpdir) / "application-settings.json")
        original_app_settings_init(self, path)

    monkeypatch.setattr(ApplicationSettings, "__init__", mock_app_settings_init)

    original_sys_path = sys.path.copy()
    sys.path.insert(0, str(workspace_root)) # Add parent dir to sys.path
    try:
        sys.modules.pop("pi_camera_in_docker.main", None)
        import pi_camera_in_docker.main as main
        cfg = main._load_config()
        cfg["app_mode"] = "webcam"
        cfg["mock_camera"] = True
        app = main.create_webcam_app(cfg)
        return app.test_client()
    finally:
        sys.path = original_sys_path


def test_webcam_control_plane_endpoints_do_not_require_auth_when_token_unset(monkeypatch):
    client = _new_webcam_client(monkeypatch, "")

    health = client.get("/health")
    ready = client.get("/ready")
    metrics = client.get("/metrics")
    status = client.get("/api/status")

    assert health.status_code == 200
    assert ready.status_code in (200, 503)
    assert metrics.status_code == 200
    assert status.status_code == 200


def test_webcam_control_plane_endpoints_require_valid_bearer_when_token_set(monkeypatch):
    client = _new_webcam_client(monkeypatch, "node-shared-token")

    unauthorized_status = client.get("/api/status")
    assert unauthorized_status.status_code == 401
    assert unauthorized_status.json["error"]["code"] == "UNAUTHORIZED"

    invalid_status = client.get("/api/status", headers={"Authorization": "Bearer wrong"})
    assert invalid_status.status_code == 401
    assert invalid_status.json["error"]["code"] == "UNAUTHORIZED"

    unauthorized_health = client.get("/health")
    assert unauthorized_health.status_code == 401
    assert unauthorized_health.json["error"]["code"] == "UNAUTHORIZED"

    invalid_health = client.get("/health", headers={"Authorization": "Bearer wrong"})
    assert invalid_health.status_code == 401
    assert invalid_health.json["error"]["code"] == "UNAUTHORIZED"

    unauthorized_action = client.post("/api/actions/restart", json={})
    assert unauthorized_action.status_code == 401
    assert unauthorized_action.json["error"]["code"] == "UNAUTHORIZED"

    unauthorized_api_test_action = client.post("/api/actions/api-test-start", json={})
    assert unauthorized_api_test_action.status_code == 401
    assert unauthorized_api_test_action.json["error"]["code"] == "UNAUTHORIZED"

    valid_headers = {"Authorization": "Bearer node-shared-token"}
    authorized_health = client.get("/health", headers=valid_headers)
    authorized_ready = client.get("/ready", headers=valid_headers)
    authorized_metrics = client.get("/metrics", headers=valid_headers)
    authorized_status = client.get("/api/status", headers=valid_headers)

    assert authorized_health.status_code == 200
    assert authorized_ready.status_code in (200, 503)
    assert authorized_metrics.status_code == 200
    assert authorized_status.status_code == 200


def _assert_render_config_contract(payload: dict):
    for key in ("camera_settings", "stream_control", "runtime", "health_check", "timestamp"):
        assert key in payload

    assert set(payload["camera_settings"]) >= {"resolution", "fps", "target_fps", "jpeg_quality"}
    assert set(payload["stream_control"]) >= {
        "max_stream_connections",
        "current_stream_connections",
        "max_frame_age_seconds",
        "cors_origins",
    }
    assert set(payload["runtime"]) >= {"camera_active", "mock_camera", "uptime_seconds"}
    assert set(payload["health_check"]) >= {
        "camera_pipeline",
        "stream_freshness",
        "connection_capacity",
        "mock_mode",
    }
    assert isinstance(payload["timestamp"], str)


def _assert_health_check_contract(payload: dict):
    allowed_states = {"ok", "warn", "fail", "unknown"}
    indicators = payload["health_check"]
    for key in (
        "camera_pipeline",
        "stream_freshness",
        "connection_capacity",
        "mock_mode",
    ):
        assert key in indicators
        indicator = indicators[key]
        assert indicator["state"] in allowed_states
        assert isinstance(indicator["label"], str)
        assert indicator["label"]
        assert isinstance(indicator["details"], str)
        assert indicator["details"]


def test_webcam_api_test_mode_transitions_and_status_contract(monkeypatch):
    client = _new_webcam_client(monkeypatch, "")

    started = client.post(
        "/api/actions/api-test-start",
        json={"interval_seconds": 0.01, "scenario_order": [0, 1, 2]},
    )
    assert started.status_code == 200
    assert started.json["api_test"] == {
        "enabled": True,
        "active": True,
        "state_index": 0,
        "state_name": "ok",
        "next_transition_seconds": started.json["api_test"]["next_transition_seconds"],
    }
    assert started.json["api_test"]["next_transition_seconds"] is not None

    first_status = client.get("/api/status")
    assert first_status.status_code == 200
    assert first_status.json["status"] == "ok"
    assert first_status.json["stream_available"] is True
    assert first_status.json["camera_active"] is True
    assert first_status.json["fps"] == 24.0
    assert first_status.json["api_test"]["active"] is True
    assert first_status.json["api_test"]["state_index"] == 0

    time.sleep(0.02)
    interval_transitioned_status = client.get("/api/status")
    assert interval_transitioned_status.status_code == 200
    assert interval_transitioned_status.json["api_test"]["state_index"] == 1
    assert interval_transitioned_status.json["status"] == "degraded"
    assert interval_transitioned_status.json["stream_available"] is False
    assert interval_transitioned_status.json["camera_active"] is True

    stepped = client.post("/api/actions/api-test-step", json={})
    assert stepped.status_code == 200
    assert stepped.json["api_test"]["active"] is False
    assert stepped.json["api_test"]["state_index"] == 2
    assert stepped.json["api_test"]["state_name"] == "degraded"
    assert stepped.json["api_test"]["next_transition_seconds"] is None

    stepped_status = client.get("/api/status")
    assert stepped_status.status_code == 200
    assert stepped_status.json["api_test"]["state_index"] == 2
    assert stepped_status.json["stream_available"] is False
    assert stepped_status.json["camera_active"] is False

    stopped = client.post("/api/actions/api-test-stop", json={})
    assert stopped.status_code == 200
    assert stopped.json["api_test"]["enabled"] is True
    assert stopped.json["api_test"]["active"] is False
    assert stopped.json["api_test"]["next_transition_seconds"] is None

    time.sleep(0.02)
    stopped_status = client.get("/api/status")
    assert stopped_status.status_code == 200
    assert stopped_status.json["api_test"]["state_index"] == 2

    reset = client.post("/api/actions/api-test-reset", json={})
    assert reset.status_code == 200
    assert reset.json["api_test"]["state_index"] == 0
    assert reset.json["api_test"]["active"] is False

    reset_status = client.get("/api/status")
    assert reset_status.status_code == 200
    assert reset_status.json["status"] == "ok"
    assert reset_status.json["stream_available"] is True
    assert reset_status.json["camera_active"] is True


def test_webcam_status_contract_reports_degraded_until_stream_is_fresh(monkeypatch):
    client = _new_webcam_client(monkeypatch, "")

    status = client.get("/api/status")
    assert status.status_code == 200
    payload = status.json

    assert payload["app_mode"] == "webcam"
    assert payload["status"] == "degraded"
    assert payload["stream_available"] is False
    assert isinstance(payload["camera_active"], bool)
    assert payload["fps"] == 0.0
    assert payload["connections"]["current"] >= 0
    assert payload["connections"]["max"] > 0


def test_webcam_stream_and_snapshot_routes_are_not_protected_by_control_plane_auth(monkeypatch):
    client = _new_webcam_client(monkeypatch, "node-shared-token")

    stream = client.get("/stream.mjpg")
    snapshot = client.get("/snapshot.jpg")

    assert stream.status_code in (200, 503)
    assert snapshot.status_code in (200, 503)


def test_webcam_action_route_requires_auth_and_returns_contract(monkeypatch):
    client = _new_webcam_client(monkeypatch, "node-shared-token")

    valid_headers = {"Authorization": "Bearer node-shared-token"}
    supported_actions = [
        "restart",
        "api-test-start",
        "api-test-stop",
        "api-test-reset",
        "api-test-step",
    ]

    restart = client.post("/api/actions/restart", json={}, headers=valid_headers)
    assert restart.status_code == 501
    assert restart.json["error"]["code"] == "ACTION_NOT_IMPLEMENTED"
    assert restart.json["error"]["details"]["supported_actions"] == supported_actions

    started = client.post(
        "/api/actions/api-test-start",
        json={"interval_seconds": 2, "scenario_order": [2, 0, 1]},
        headers=valid_headers,
    )
    assert started.status_code == 200
    assert started.json["ok"] is True
    assert started.json["api_test"]["enabled"] is True
    assert started.json["api_test"]["active"] is True
    assert started.json["api_test"]["state_name"] in {"ok", "degraded"}
    assert started.json["api_test"]["next_transition_seconds"] is not None

    stepped = client.post("/api/actions/api-test-step", json={}, headers=valid_headers)
    assert stepped.status_code == 200
    assert stepped.json["api_test"]["active"] is False

    reset = client.post("/api/actions/api-test-reset", json={}, headers=valid_headers)
    assert reset.status_code == 200
    assert reset.json["api_test"]["state_index"] == 0

    invalid = client.post(
        "/api/actions/api-test-start",
        json={"interval_seconds": 0},
        headers=valid_headers,
    )
    assert invalid.status_code == 400
    assert invalid.json["error"]["code"] == "ACTION_INVALID_BODY"

    unsupported = client.post("/api/actions/refresh", json={}, headers=valid_headers)
    assert unsupported.status_code == 400
    assert unsupported.json["error"]["code"] == "ACTION_UNSUPPORTED"
    assert unsupported.json["error"]["details"]["supported_actions"] == supported_actions
