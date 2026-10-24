"""
Unit tests for Flask application components.
Tests without requiring camera hardware.
"""

import sys
import uuid
from pathlib import Path

import pytest


# Add workspace root to sys.path for proper package imports
workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root))


@pytest.mark.parametrize(
    ("present_paths", "expected_counts", "expected_warnings"),
    [
        (
            {
                "/dev/vchiq",
                "/dev/video0",
                "/dev/video1",
                "/dev/media0",
                "/dev/v4l-subdev0",
                "/dev/dma_heap/linux,cma",
                "/dev/dma_heap/system",
            },
            ("video=2", "media=1", "v4l_subdev=1", "dma_heap=2"),
            (),
        ),
        (
            {"/dev/vchiq", "/dev/video0", "/dev/dma_heap/system"},
            ("video=1", "media=0", "v4l_subdev=0", "dma_heap=1"),
            (),
        ),
        (
            {"/dev/vchiq", "/dev/media0", "/dev/v4l-subdev0"},
            ("video=0", "media=1", "v4l_subdev=1", "dma_heap=0"),
            ("partial node availability", "Streaming is likely unavailable"),
        ),
        (
            set(),
            ("video=0", "media=0", "v4l_subdev=0", "dma_heap=0"),
            (
                "Critical camera devices not found",
                "Camera enumeration is likely to fail in this container",
                "Verify host camera drivers and container device mappings",
            ),
        ),
    ],
    ids=("complete-inventory", "video-node-is-sufficient", "partial-inventory", "empty-inventory"),
)
def test_device_preflight_reports_inventory_and_actionable_warnings(
    monkeypatch, present_paths, expected_counts, expected_warnings
):
    """Device preflight summarizes detected nodes and warns when streaming is unavailable."""
    from pi_camera_in_docker import main

    monkeypatch.setattr(Path, "exists", lambda path: str(path) in present_paths)
    info_logs = []
    warning_logs = []
    monkeypatch.setattr(
        main.logger, "info", lambda msg, *args: info_logs.append(msg % args if args else msg)
    )
    monkeypatch.setattr(
        main.logger,
        "warning",
        lambda msg, *args: warning_logs.append(msg % args if args else msg),
    )

    main._check_device_availability({"mock_camera": False})

    preflight = next(entry for entry in info_logs if "Camera preflight:" in entry)
    for expected_count in expected_counts:
        assert expected_count in preflight
    joined_warnings = "\n".join(warning_logs)
    for expected_warning in expected_warnings:
        assert expected_warning in joined_warnings
    if not expected_warnings:
        assert warning_logs == []


def test_frame_buffer_write_updates_stats_and_latest_frame(monkeypatch):
    """FrameBuffer writes should update latest frame and stream stats deterministically."""
    from pi_camera_in_docker.modes import webcam as webcam_mode

    timestamps = iter([100.0, 101.0])
    monkeypatch.setattr(webcam_mode.time, "monotonic", lambda: next(timestamps))

    stats = webcam_mode.StreamStats()
    output = webcam_mode.FrameBuffer(stats, target_fps=0)

    assert output.write(b"frame-1") == 7
    assert output.write(b"frame-2") == 7
    assert output.frame == b"frame-2"

    frame_count, last_frame_time, current_fps = stats.snapshot()
    assert frame_count == 2
    assert last_frame_time == 101.0
    assert current_fps == 1.0


def test_healthcheck_url_validation_allows_valid_hostname(monkeypatch):
    """Ensure valid HEALTHCHECK_URL hostnames pass validation."""
    import urllib.request

    import healthcheck

    captured = {}

    class DummyResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(url, timeout=None):
        captured["url"] = url
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setenv("HEALTHCHECK_URL", "http://example.com/health")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert healthcheck.check_health() is True
    assert captured["url"] == "http://example.com/health"


def test_get_camera_info_prefers_class_inventory_over_module_fallback(monkeypatch):
    """Camera discovery uses the class API when both supported APIs are available."""
    import types

    from pi_camera_in_docker import main

    class FakePicamera2:
        @staticmethod
        def global_camera_info():
            return [{"id": "class-camera"}]

    fake_module = types.ModuleType("picamera2")

    def module_global_camera_info():
        return [{"id": "module-camera"}]

    fake_module.global_camera_info = module_global_camera_info
    monkeypatch.setitem(sys.modules, "picamera2", fake_module)

    camera_info, detection_path = main._get_camera_info(FakePicamera2)

    assert camera_info == [{"id": "class-camera"}]
    assert detection_path == "Picamera2.global_camera_info"


def test_get_camera_info_falls_back_to_module_inventory_when_class_query_fails(monkeypatch):
    """Camera discovery falls back to the module API when the class query raises."""
    import types

    from pi_camera_in_docker import main

    class FakePicamera2:
        @staticmethod
        def global_camera_info():
            raise RuntimeError("class API unavailable")

    fake_module = types.ModuleType("picamera2")

    def module_global_camera_info():
        return [{"id": "module-camera"}]

    fake_module.global_camera_info = module_global_camera_info
    monkeypatch.setitem(sys.modules, "picamera2", fake_module)

    camera_info, detection_path = main._get_camera_info(FakePicamera2)

    assert camera_info == [{"id": "module-camera"}]
    assert detection_path == "picamera2.global_camera_info"


def test_get_camera_info_returns_empty_inventory_when_no_query_api_is_available(monkeypatch):
    """Camera discovery reports no inventory when neither supported API is available."""
    import types

    from pi_camera_in_docker import main

    class FakePicamera2:
        pass

    monkeypatch.setitem(sys.modules, "picamera2", types.ModuleType("picamera2"))

    camera_info, detection_path = main._get_camera_info(FakePicamera2)

    assert camera_info == []
    assert detection_path == "none"


def test_run_webcam_mode_logs_device_inventory_when_no_cameras_detected(monkeypatch):
    """No-camera startup should log inventory and keep webcam mode degraded without raising."""
    from threading import Event, RLock

    pytest.importorskip("flask")
    from modes.webcam import ConnectionTracker, FrameBuffer, StreamStats

    from pi_camera_in_docker import main

    # Minimal config for no-camera scenario
    cfg = {
        "mock_camera": False,
        "pykms_mock_fallback_enabled": False,
        "resolution": (640, 480),
        "fps": 0,
        "jpeg_quality": 90,
        "target_fps": 0,
        "max_frame_age_seconds": 10.0,
        "max_stream_connections": 10,
    }

    # Build state dict
    stream_stats = StreamStats()
    output = FrameBuffer(stream_stats, target_fps=cfg["target_fps"])
    state = {
        "recording_started": Event(),
        "shutdown_requested": Event(),
        "camera_lock": RLock(),
        "output": output,
        "stream_stats": stream_stats,
        "connection_tracker": ConnectionTracker(),
        "max_stream_connections": cfg["max_stream_connections"],
        "picam2_instance": None,
        "camera_startup_error": None,
    }

    # Minimal fake camera classes
    class FakePicamera2:
        pass

    class FakeJpegEncoder:
        def __init__(self, q):
            self.quality = q

    class FakeFileOutput:
        def __init__(self, out):
            self.output = out

    # Device inventory mock
    inventory = {
        "video_devices": ["/dev/video0"],
        "media_devices": ["/dev/media0"],
        "v4l_subdev_devices": ["/dev/v4l-subdev0"],
        "dma_heap_devices": ["/dev/dma_heap/system"],
        "vchiq_device": True,
    }

    # Capture logger calls
    error_calls = []

    def fake_error(msg, *args, **kwargs):
        error_calls.append((msg, kwargs))

    # Setup mocks for all external dependencies
    monkeypatch.setattr(main, "_check_device_availability", lambda _cfg: None)
    monkeypatch.setattr(
        main, "import_camera_components", lambda _: (FakePicamera2, FakeJpegEncoder, FakeFileOutput)
    )
    monkeypatch.setattr(main, "_detect_camera_devices", lambda: inventory)
    monkeypatch.setattr(main, "_get_camera_info", lambda _cls: ([], "test.path"))
    monkeypatch.setattr(main.logger, "error", fake_error)

    # Run webcam mode with no cameras
    main._run_webcam_mode(state, cfg)

    # Verify webcam mode enters degraded state
    assert not state["recording_started"].is_set()
    startup_error = state["camera_startup_error"]
    assert startup_error is not None
    assert startup_error["code"] == "CAMERA_UNAVAILABLE"
    assert startup_error["reason"] == "camera_unavailable"

    # Verify structured error logging includes inventory
    assert error_calls, "Expected error logging when cameras unavailable"
    assert error_calls[0][0] == "No cameras detected by picamera2 enumeration"

    logged_extra = error_calls[0][1].get("extra", {})
    assert logged_extra["camera_info_detection_path"] == "test.path"
    assert logged_extra["camera_device_inventory"] == {
        "video_devices": ["/dev/video0"],
        "media_devices": ["/dev/media0"],
        "v4l_subdev_devices": ["/dev/v4l-subdev0"],
        "dma_heap_devices": ["/dev/dma_heap/system"],
        "vchiq_exists": True,
    }


def test_shutdown_camera_clears_recording_started_for_real_camera_path():
    """Shutdown should clear recording_started and stop an active real camera instance."""
    from threading import Event, RLock

    from pi_camera_in_docker import main

    class FakePicam:
        def __init__(self):
            self.started = True
            self.stop_calls = 0

        def stop_recording(self):
            self.stop_calls += 1

    picam = FakePicam()
    recording_started = Event()
    recording_started.set()

    state = {
        "shutdown_requested": Event(),
        "recording_started": recording_started,
        "camera_lock": RLock(),
        "picam2_instance": picam,
    }

    main._shutdown_camera(state)

    assert state["shutdown_requested"].is_set()
    assert not state["recording_started"].is_set()
    assert picam.stop_calls == 1
    assert state["picam2_instance"] is None


def test_handle_shutdown_stops_discovery_without_touching_camera_shutdown_flag():
    """Shutdown handler should stop discovery announcer explicitly before camera shutdown."""
    from threading import Event
    from unittest.mock import patch

    from flask import Flask

    from pi_camera_in_docker import main

    class FakeAnnouncer:
        def __init__(self):
            self.stop_calls = 0

        def stop(self):
            self.stop_calls += 1

    app = Flask(__name__)
    app.motion_state = {
        "discovery_announcer": FakeAnnouncer(),
        "discovery_shutdown_event": Event(),
        "shutdown_requested": Event(),
    }

    observed = {}

    def fake_shutdown_camera(state):
        observed["shutdown_requested_before"] = state["shutdown_requested"].is_set()
        observed["discovery_shutdown_before"] = state["discovery_shutdown_event"].is_set()

    with (
        pytest.raises(SystemExit) as excinfo,
        patch.object(main, "_shutdown_camera", side_effect=fake_shutdown_camera),
    ):
        main.handle_shutdown(app, 15, None)

    assert excinfo.value.code == 15
    assert app.motion_state["discovery_announcer"].stop_calls == 1
    assert observed["shutdown_requested_before"] is False
    assert observed["discovery_shutdown_before"] is True


def test_shutdown_updates_ready_metrics_and_api_status_immediately():
    """Control-plane status routes should reflect shutdown without waiting for frame thread teardown."""
    from pi_camera_in_docker import main
    from pi_camera_in_docker.shared import register_shared_routes

    app, _limiter, state = main._create_base_app(
        {
            "app_mode": "webcam",
            "resolution": (640, 480),
            "fps": 0,
            "target_fps": 0,
            "jpeg_quality": 90,
            "max_frame_age_seconds": 10.0,
            "max_stream_connections": 10,
            "pi3_profile_enabled": False,
            "mock_camera": True,
            "cors_enabled": False,
            "pykms_mock_fallback_enabled": False,
            "webcam_registry_path": "/tmp/node-registry.json",
            "application_settings_path": "/tmp/application-settings.json",
            "management_auth_token": "",
            "webcam_control_plane_auth_token": "",
        }
    )

    register_shared_routes(
        app,
        state,
        get_stream_status=lambda: {
            "frames_captured": 7,
            "current_fps": 12.5,
            "last_frame_age_seconds": 0.1,
        },
    )

    state["recording_started"].set()
    client = app.test_client()

    assert client.get("/ready").status_code == 200
    assert client.get("/metrics").get_json()["camera_active"] is True
    assert client.get("/api/status").get_json()["camera_active"] is True

    main._shutdown_camera(state)

    ready = client.get("/ready")
    metrics = client.get("/metrics")
    api_status = client.get("/api/status")

    assert ready.status_code == 503
    assert ready.get_json()["status"] == "not_ready"
    assert metrics.get_json()["camera_active"] is False
    assert api_status.get_json()["camera_active"] is False
    assert api_status.get_json()["stream_available"] is False


def test_ready_reports_initializing_reason_when_camera_startup_error_absent():
    """Webcam /ready should distinguish normal startup wait from startup failure states."""
    from pi_camera_in_docker import main
    from pi_camera_in_docker.shared import register_shared_routes

    app, _limiter, state = main._create_base_app(
        {
            "app_mode": "webcam",
            "resolution": (640, 480),
            "fps": 0,
            "target_fps": 0,
            "jpeg_quality": 90,
            "max_frame_age_seconds": 10.0,
            "max_stream_connections": 5,
            "pi3_profile_enabled": False,
            "mock_camera": True,
            "cors_enabled": False,
            "pykms_mock_fallback_enabled": False,
            "webcam_registry_path": "/tmp/node-registry.json",
            "application_settings_path": "/tmp/application-settings.json",
            "management_auth_token": "",
            "webcam_control_plane_auth_token": "",
        }
    )

    register_shared_routes(
        app,
        state,
        get_stream_status=lambda: {
            "frames_captured": 0,
            "current_fps": 0.0,
            "last_frame_age_seconds": None,
        },
    )

    response = app.test_client().get("/ready")

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["status"] == "not_ready"
    assert payload["reason"] == "initializing"
    assert "camera_error" not in payload


def _build_base_app_config(cors_enabled=False, cors_origins="disabled"):
    return {
        "app_mode": "webcam",
        "resolution": (640, 480),
        "fps": 0,
        "target_fps": 0,
        "jpeg_quality": 90,
        "max_frame_age_seconds": 10.0,
        "max_stream_connections": 10,
        "pi3_profile_enabled": False,
        "mock_camera": True,
        "cors_enabled": cors_enabled,
        "cors_origins": cors_origins,
        "pykms_mock_fallback_enabled": False,
        "webcam_registry_path": "/tmp/node-registry.json",
        "application_settings_path": "/tmp/application-settings.json",
        "management_auth_token": "",
        "webcam_control_plane_auth_token": "",
    }


def test_register_middleware_keeps_cors_disabled_when_feature_off():
    from pi_camera_in_docker import main

    app, _limiter, _state = main._create_base_app(
        _build_base_app_config(cors_enabled=False, cors_origins="https://allowed.example")
    )

    response = app.test_client().get("/api/config", headers={"Origin": "https://allowed.example"})

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


def test_register_middleware_applies_wildcard_cors_policy_from_config():
    from pi_camera_in_docker import main

    app, _limiter, _state = main._create_base_app(
        _build_base_app_config(cors_enabled=True, cors_origins="*")
    )

    response = app.test_client().get("/api/config", headers={"Origin": "https://random.example"})

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "*"


def test_register_middleware_applies_explicit_cors_origins_from_config():
    from pi_camera_in_docker import main

    app, _limiter, _state = main._create_base_app(
        _build_base_app_config(
            cors_enabled=True,
            cors_origins="https://one.example, https://two.example",
        )
    )
    client = app.test_client()

    allowed = client.get("/api/config", headers={"Origin": "https://one.example"})
    blocked = client.get("/api/config", headers={"Origin": "https://blocked.example"})

    assert allowed.status_code == 200
    assert allowed.headers.get("Access-Control-Allow-Origin") == "https://one.example"
    assert blocked.status_code == 200
    assert "Access-Control-Allow-Origin" not in blocked.headers


def test_register_middleware_handles_cors_preflight_without_extension():
    """Allowed preflight requests receive requested headers and origin variation."""
    from pi_camera_in_docker import main

    app, _limiter, _state = main._create_base_app(
        _build_base_app_config(
            cors_enabled=True,
            cors_origins="https://one.example, https://two.example",
        )
    )

    response = app.test_client().options(
        "/api/config",
        headers={
            "Origin": "https://one.example",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "https://one.example"
    assert "PATCH" in response.headers.get("Access-Control-Allow-Methods", "")
    assert response.headers.get("Access-Control-Allow-Headers") == "authorization, content-type"
    assert "Origin" in response.headers.get("Vary", "")


def test_register_middleware_rejects_unconfigured_cors_preflight_origin():
    """Preflight requests from unconfigured origins receive no CORS permission."""
    from pi_camera_in_docker import main

    app, _limiter, _state = main._create_base_app(
        _build_base_app_config(cors_enabled=True, cors_origins="https://one.example")
    )
    response = app.test_client().options(
        "/api/config",
        headers={
            "Origin": "https://blocked.example",
            "Access-Control-Request-Method": "PATCH",
        },
    )

    assert "Access-Control-Allow-Origin" not in response.headers


def test_register_middleware_preserves_inbound_correlation_id():
    """Middleware should preserve inbound X-Correlation-ID values."""
    from pi_camera_in_docker import main

    app, _limiter, _state = main._create_base_app(_build_base_app_config())
    correlation_id = "cid-from-client"

    response = app.test_client().get("/api/config", headers={"X-Correlation-ID": correlation_id})

    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == correlation_id


def test_register_middleware_generates_correlation_id_when_missing():
    """Middleware should generate a UUID correlation ID when request header is absent."""
    from pi_camera_in_docker import main

    app, _limiter, _state = main._create_base_app(_build_base_app_config())

    response = app.test_client().get("/api/config")
    generated_correlation_id = response.headers.get("X-Correlation-ID")

    assert response.status_code == 200
    assert generated_correlation_id
    assert uuid.UUID(generated_correlation_id)


def test_run_webcam_mode_raises_on_camera_init_failure_in_strict_mode(monkeypatch):
    """Strict camera init mode should preserve raise-and-exit startup behavior."""
    from threading import Event, RLock

    from modes.webcam import ConnectionTracker, FrameBuffer, StreamStats

    from pi_camera_in_docker import main

    cfg = {
        "mock_camera": False,
        "fail_on_camera_init_error": True,
        "target_fps": 0,
        "max_stream_connections": 10,
    }

    stream_stats = StreamStats()
    output = FrameBuffer(stream_stats, target_fps=cfg["target_fps"])
    state = {
        "recording_started": Event(),
        "shutdown_requested": Event(),
        "camera_lock": RLock(),
        "output": output,
        "stream_stats": stream_stats,
        "connection_tracker": ConnectionTracker(),
        "max_stream_connections": cfg["max_stream_connections"],
        "picam2_instance": None,
    }

    monkeypatch.setattr(main, "_check_device_availability", lambda _cfg: None)

    def set_runtime_startup_error(_state, _cfg):
        _state["camera_startup_error"] = {
            "code": "CAMERA_STARTUP_FAILED",
            "reason": "camera_unavailable",
            "message": "boom",
        }

    monkeypatch.setattr(main, "_init_real_camera", set_runtime_startup_error)

    with pytest.raises(RuntimeError, match="boom"):
        main._run_webcam_mode(state, cfg)


def test_run_webcam_mode_explicit_mock_camera_forces_mock_path(monkeypatch):
    """Explicit mock mode should bypass real camera init and use mock frames."""
    from threading import Event, RLock

    from modes.webcam import ConnectionTracker, FrameBuffer, StreamStats

    from pi_camera_in_docker import main

    cfg = {
        "mock_camera": True,
        "fail_on_camera_init_error": True,
        "target_fps": 0,
        "max_stream_connections": 10,
    }

    stream_stats = StreamStats()
    output = FrameBuffer(stream_stats, target_fps=cfg["target_fps"])
    state = {
        "recording_started": Event(),
        "shutdown_requested": Event(),
        "camera_lock": RLock(),
        "output": output,
        "stream_stats": stream_stats,
        "connection_tracker": ConnectionTracker(),
        "max_stream_connections": cfg["max_stream_connections"],
        "picam2_instance": None,
    }

    monkeypatch.setattr(main, "_check_device_availability", lambda _cfg: None)

    real_camera_called = []

    def fail_if_real_camera_called(_state, _cfg):
        real_camera_called.append(True)

    mock_camera_called = []

    def fake_mock_frames(_state, _cfg):
        mock_camera_called.append(True)
        _state["recording_started"].set()

    monkeypatch.setattr(main, "_init_real_camera", fail_if_real_camera_called)
    monkeypatch.setattr(main, "_init_mock_camera_frames", fake_mock_frames)

    main._run_webcam_mode(state, cfg)

    assert mock_camera_called
    assert not real_camera_called
    assert state["recording_started"].is_set() is True
    assert state["active_mock_fallback"] is False


def test_run_webcam_mode_falls_back_to_mock_on_camera_init_failure_when_not_strict(monkeypatch):
    """Non-strict camera init mode should activate mock fallback on camera failures."""
    from threading import Event, RLock

    from modes.webcam import ConnectionTracker, FrameBuffer, StreamStats

    from pi_camera_in_docker import main

    cfg = {
        "mock_camera": False,
        "fail_on_camera_init_error": False,
        "target_fps": 0,
        "max_stream_connections": 10,
    }

    stream_stats = StreamStats()
    output = FrameBuffer(stream_stats, target_fps=cfg["target_fps"])
    state = {
        "recording_started": Event(),
        "shutdown_requested": Event(),
        "camera_lock": RLock(),
        "output": output,
        "stream_stats": stream_stats,
        "connection_tracker": ConnectionTracker(),
        "max_stream_connections": cfg["max_stream_connections"],
        "picam2_instance": None,
    }

    warnings = []

    monkeypatch.setattr(main, "_check_device_availability", lambda _cfg: None)

    def set_runtime_startup_error(_state, _cfg):
        _state["camera_startup_error"] = {
            "code": "CAMERA_STARTUP_FAILED",
            "reason": "camera_unavailable",
        }

    monkeypatch.setattr(main, "_init_real_camera", set_runtime_startup_error)

    fallback_called = []

    def fake_mock_fallback(_state, _cfg):
        fallback_called.append(True)
        _state["recording_started"].set()

    monkeypatch.setattr(main, "_init_mock_camera_frames", fake_mock_fallback)
    monkeypatch.setattr(
        main.logger,
        "warning",
        lambda message, *args, **kwargs: warnings.append((message, kwargs)),
    )

    main._run_webcam_mode(state, cfg)

    assert state["recording_started"].is_set() is True
    assert state["active_mock_fallback"] is True
    assert fallback_called
    assert warnings
    assert "activating mock fallback" in warnings[0][0]


def test_run_webcam_mode_forced_real_camera_still_falls_back_when_not_strict(monkeypatch):
    """Explicit MOCK_CAMERA=false should still permit fallback in non-strict mode."""
    from threading import Event, RLock

    from modes.webcam import ConnectionTracker, FrameBuffer, StreamStats

    from pi_camera_in_docker import main

    cfg = {
        "mock_camera": False,
        "fail_on_camera_init_error": False,
        "target_fps": 0,
        "max_stream_connections": 10,
    }

    stream_stats = StreamStats()
    output = FrameBuffer(stream_stats, target_fps=cfg["target_fps"])
    state = {
        "recording_started": Event(),
        "shutdown_requested": Event(),
        "camera_lock": RLock(),
        "output": output,
        "stream_stats": stream_stats,
        "connection_tracker": ConnectionTracker(),
        "max_stream_connections": cfg["max_stream_connections"],
        "picam2_instance": None,
    }

    monkeypatch.setattr(main, "_check_device_availability", lambda _cfg: None)

    def set_permission_error(_state, _cfg):
        _state["camera_startup_error"] = {
            "code": "CAMERA_PERMISSION_DENIED",
            "reason": "camera_unavailable",
        }

    monkeypatch.setattr(main, "_init_real_camera", set_permission_error)

    fallback_called = []

    def fake_mock_fallback(_state, _cfg):
        fallback_called.append(True)

    monkeypatch.setattr(main, "_init_mock_camera_frames", fake_mock_fallback)

    main._run_webcam_mode(state, cfg)

    assert fallback_called
    assert state["active_mock_fallback"] is True


def test_api_config_runtime_includes_mock_fallback_observability_fields(monkeypatch):
    """Runtime config payload should expose configured mock and active fallback state."""
    from pi_camera_in_docker import feature_flags, main, runtime_config

    monkeypatch.setenv("MIO_APP_MODE", "webcam")
    monkeypatch.setenv("MIO_MOCK_CAMERA", "false")

    flags = feature_flags.FeatureFlags()
    flags.load()
    monkeypatch.setattr(runtime_config, "is_flag_enabled", flags.is_enabled)
    monkeypatch.setattr(main, "_run_webcam_mode", lambda _state, _cfg: None)

    app = main.create_webcam_app()
    app.motion_state["active_mock_fallback"] = True

    response = app.test_client().get("/api/config")

    assert response.status_code == 200
    runtime = response.get_json()["runtime"]
    assert runtime["mock_camera"] is False
    assert runtime["configured_mock_camera"] is False
    assert runtime["active_mock_fallback"] is True


def test_init_mock_camera_frames_generates_non_empty_frames_from_mio_renderer(monkeypatch):
    """Mock frame init should publish non-empty JPEG bytes from Mio renderer output."""
    from threading import Event
    from types import SimpleNamespace

    from pi_camera_in_docker import main

    writes = []

    class OutputStub:
        def write(self, frame):
            writes.append(frame)

    class ImmediateThread:
        def __init__(self, target, daemon):
            self._target = target
            self._daemon = daemon

        def start(self):
            self._target()

    state = {
        "recording_started": Event(),
        "shutdown_requested": Event(),
        "output": OutputStub(),
    }
    cfg = {"resolution": (640, 480), "jpeg_quality": 88, "fps": 30}
    rendered_frame = b"\xff\xd8\xffmio-jpeg-bytes"

    monkeypatch.setattr(main, "render_mio_mock_frame", lambda *_args, **_kwargs: rendered_frame)
    monkeypatch.setattr(
        main,
        "time",
        SimpleNamespace(sleep=lambda *_args, **_kwargs: state["shutdown_requested"].set()),
    )
    monkeypatch.setattr(main, "Thread", ImmediateThread)

    main._init_mock_camera_frames(state, cfg)

    # The immediate fake thread completes synchronously and clears this event in
    # its finally block; the write assertion below confirms the loop started.
    assert state["recording_started"].is_set() is False
    assert writes
    assert writes[0] == rendered_frame
    assert len(writes[0]) > 0


def test_init_mock_camera_frames_uses_black_frame_fallback_on_render_failure(monkeypatch):
    """Mock frame init should switch to black-frame JPEG fallback when rendering fails."""
    from threading import Event
    from types import SimpleNamespace

    from pi_camera_in_docker import main
    from pi_camera_in_docker.mock_stream_renderer import MockStreamRenderError

    writes = []

    class OutputStub:
        def write(self, frame):
            writes.append(frame)

    class ImmediateThread:
        def __init__(self, target, daemon):
            self._target = target
            self._daemon = daemon

        def start(self):
            self._target()

    state = {
        "recording_started": Event(),
        "shutdown_requested": Event(),
        "output": OutputStub(),
    }
    cfg = {"resolution": (640, 480), "jpeg_quality": 75, "fps": 20}

    def raise_render_error(*_args, **_kwargs):
        raise MockStreamRenderError("boom")

    monkeypatch.setattr(main, "render_mio_mock_frame", raise_render_error)
    monkeypatch.setattr(
        main,
        "time",
        SimpleNamespace(sleep=lambda *_args, **_kwargs: state["shutdown_requested"].set()),
    )
    monkeypatch.setattr(main, "Thread", ImmediateThread)

    main._init_mock_camera_frames(state, cfg)

    assert writes
    assert writes[0][:3] == b"\xff\xd8\xff"
    assert len(writes[0]) > 3


def test_run_webcam_mode_raises_unexpected_camera_exception_even_when_not_strict(monkeypatch):
    """Unexpected camera init exceptions should propagate even when strict mode is disabled."""
    from threading import Event, RLock

    from modes.webcam import ConnectionTracker, FrameBuffer, StreamStats

    from pi_camera_in_docker import main

    cfg = {
        "mock_camera": False,
        "fail_on_camera_init_error": False,
        "target_fps": 0,
        "max_stream_connections": 10,
    }

    stream_stats = StreamStats()
    output = FrameBuffer(stream_stats, target_fps=cfg["target_fps"])
    state = {
        "recording_started": Event(),
        "shutdown_requested": Event(),
        "camera_lock": RLock(),
        "output": output,
        "stream_stats": stream_stats,
        "connection_tracker": ConnectionTracker(),
        "max_stream_connections": cfg["max_stream_connections"],
        "picam2_instance": None,
        "camera_startup_error": {"reason": "camera_exception"},
    }

    monkeypatch.setattr(main, "_check_device_availability", lambda _cfg: None)

    def raise_value_error(_state, _cfg):
        raise ValueError("bad programming error")

    monkeypatch.setattr(main, "_init_real_camera", raise_value_error)

    with pytest.raises(ValueError, match="bad programming error"):
        main._run_webcam_mode(state, cfg)
