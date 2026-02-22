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


def test_check_device_availability_logs_preflight_with_nodes_present(monkeypatch):
    """Preflight should summarize discovered node counts and samples."""
    from pathlib import Path

    from pi_camera_in_docker import main

    def fake_glob(self, pattern):
        matches = {
            "/dev/video*": [Path("/dev/video0"), Path("/dev/video1")],
            "/dev/media*": [Path("/dev/media0")],
            "/dev/v4l-subdev*": [Path("/dev/v4l-subdev0")],
            "/dev/dma_heap/*": [Path("/dev/dma_heap/linux,cma"), Path("/dev/dma_heap/system")],
        }
        return matches.get(pattern, [])

    # Mock Path.is_dir() and Path.exists() for specific paths
    # (these are instance methods, so we need to patch the class)
    def mock_path_is_dir(self):
        return str(self) == "/dev/dma_heap"

    def mock_path_exists(self):
        # We also need to mock specific device paths to exist
        return str(self) in [
            "/dev/vchiq",
            "/dev/video0",
            "/dev/video1",
            "/dev/media0",
            "/dev/v4l-subdev0",
            "/dev/dri",
            "/dev/dma_heap/linux,cma",
            "/dev/dma_heap/system",
        ]

    monkeypatch.setattr(Path, "glob", fake_glob)
    monkeypatch.setattr(Path, "is_dir", mock_path_is_dir)
    monkeypatch.setattr(Path, "exists", mock_path_exists)

    logged_info = []
    monkeypatch.setattr(
        main.logger, "info", lambda msg, *args: logged_info.append(msg % args if args else msg)
    )

    main._check_device_availability({"mock_camera": False})

    preflight_logs = [entry for entry in logged_info if "Camera preflight device summary" in entry]
    assert preflight_logs
    assert "'video': 2" in preflight_logs[0]
    assert "'/dev/video0'" in preflight_logs[0]
    assert "'/dev/dma_heap/linux,cma'" in preflight_logs[0]


def test_check_device_availability_does_not_warn_when_video_nodes_exist(monkeypatch):
    """Preflight should not warn for missing non-video node groups when video nodes exist."""
    from pathlib import Path

    from pi_camera_in_docker import main

    def fake_glob(self, pattern):
        matches = {
            "/dev/video*": [Path("/dev/video0")],
            "/dev/media*": [],
            "/dev/v4l-subdev*": [],
            "/dev/dma_heap/*": [Path("/dev/dma_heap/system")],
        }
        return matches.get(pattern, [])

    def mock_path_is_dir(self):
        return str(self) == "/dev/dma_heap"

    def mock_path_exists(self):
        return str(self) in ["/dev/vchiq", "/dev/video0", "/dev/media0", "/dev/dma_heap/system"]

    monkeypatch.setattr(Path, "glob", fake_glob)
    monkeypatch.setattr(Path, "is_dir", mock_path_is_dir)
    monkeypatch.setattr(Path, "exists", mock_path_exists)

    logged_warning = []
    monkeypatch.setattr(
        main.logger,
        "warning",
        lambda msg, *args: logged_warning.append(msg % args if args else msg),
    )

    main._check_device_availability({"mock_camera": False})

    assert not logged_warning


def test_check_device_availability_warns_when_video_nodes_missing(monkeypatch):
    """Preflight should warn when no video node is present, even if others exist."""
    from pathlib import Path

    from pi_camera_in_docker import main

    def fake_glob(self, pattern):
        matches = {
            "/dev/video*": [],
            "/dev/media*": [Path("/dev/media0")],
            "/dev/v4l-subdev*": [Path("/dev/v4l-subdev0")],
            "/dev/dma_heap/*": [Path("/dev/dma_heap/system")],
        }
        return matches.get(pattern, [])

    def mock_path_is_dir(self):
        return str(self) == "/dev/dma_heap"

    def mock_path_exists(self):
        return str(self) in [
            "/dev/vchiq",
            "/dev/media0",
            "/dev/v4l-subdev0",
            "/dev/dma_heap/system",
        ]

    monkeypatch.setattr(Path, "glob", fake_glob)
    monkeypatch.setattr(Path, "is_dir", mock_path_is_dir)
    monkeypatch.setattr(Path, "exists", mock_path_exists)

    logged_warning = []
    monkeypatch.setattr(
        main.logger,
        "warning",
        lambda msg, *args: logged_warning.append(msg % args if args else msg),
    )

    main._check_device_availability({"mock_camera": False})

    joined_warning = "\n".join(logged_warning)
    assert "Camera device preflight found partial node availability" in joined_warning
    assert "Streaming is likely unavailable" in joined_warning


def test_check_device_availability_warns_when_no_camera_nodes_detected(monkeypatch):
    """No video/media/subdev nodes should trigger stronger enumeration warning."""
    from pathlib import Path

    from pi_camera_in_docker import main

    monkeypatch.setattr(Path, "glob", lambda self, pattern: [])
    monkeypatch.setattr(Path, "exists", lambda self: False)

    logged_warning = []
    monkeypatch.setattr(
        main.logger,
        "warning",
        lambda msg, *args: logged_warning.append(msg % args if args else msg),
    )

    main._check_device_availability({"mock_camera": False})

    joined_warning = "\n".join(logged_warning)
    assert "Critical camera devices not found" in joined_warning
    assert "Camera enumeration is likely to fail in this container" in joined_warning
    assert "Verify host camera drivers and container device mappings" in joined_warning


def test_management_app_registers_core_routes(monkeypatch, tmp_path):
    """Management app should expose core UI, health, and management API routes."""
    from pi_camera_in_docker import main

    monkeypatch.setenv("MIO_APP_MODE", "management")
    monkeypatch.setenv("MIO_MOCK_CAMERA", "true")
    monkeypatch.setenv("MIO_NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MIO_APPLICATION_SETTINGS_PATH", str(tmp_path / "application-settings.json"))
    monkeypatch.setenv("MIO_MANAGEMENT_AUTH_TOKEN", "")

    app = main.create_management_app()
    registered_routes = {rule.rule for rule in app.url_map.iter_rules()}

    expected_routes = {
        "/",
        "/health",
        "/ready",
        "/metrics",
        "/api/config",
        "/api/webcams",
        "/api/management/overview",
    }
    assert expected_routes.issubset(registered_routes), (
        f"Missing routes: {expected_routes - registered_routes}"
    )


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


def test_get_camera_info_prefers_module_level_global_camera_info(monkeypatch):
    """Camera detection should work when picamera2 exposes module-level global_camera_info."""
    import importlib
    import sys
    import tempfile
    import types

    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("NODE_REGISTRY_PATH", f"{tmpdir}/registry.json")
        monkeypatch.setenv("MIO_APP_MODE", "management")
        monkeypatch.setenv("MIO_MOCK_CAMERA", "true")

        fake_module = types.ModuleType("picamera2")

        class FakePicamera2:
            pass

        fake_module.Picamera2 = FakePicamera2
        fake_module.global_camera_info = lambda: [{"id": "cam0"}]

        sys.modules["picamera2"] = fake_module
        sys.modules.pop("main", None)
        main = importlib.import_module("pi_camera_in_docker.main")

        camera_info, detection_path = main._get_camera_info(FakePicamera2)

        assert camera_info == [{"id": "cam0"}]
        assert detection_path == "picamera2.global_camera_info"

        sys.modules.pop("main", None)
        sys.modules.pop("picamera2", None)


def test_get_camera_info_falls_back_to_class_method(monkeypatch):
    """Camera detection should fallback to Picamera2.global_camera_info when needed."""
    import importlib
    import sys
    import tempfile
    import types

    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("NODE_REGISTRY_PATH", f"{tmpdir}/registry.json")
        monkeypatch.setenv("MIO_APP_MODE", "management")
        monkeypatch.setenv("MIO_MOCK_CAMERA", "true")

        fake_module = types.ModuleType("picamera2")

        class FakePicamera2:
            @staticmethod
            def global_camera_info():
                return [{"id": "cam1"}]

        fake_module.Picamera2 = FakePicamera2
        sys.modules["picamera2"] = fake_module

        sys.modules.pop("main", None)
        main = importlib.import_module("pi_camera_in_docker.main")

        camera_info, detection_path = main._get_camera_info(FakePicamera2)

        assert camera_info == [{"id": "cam1"}]
        assert detection_path == "Picamera2.global_camera_info"

        sys.modules.pop("main", None)
        sys.modules.pop("picamera2", None)


def test_run_webcam_mode_logs_device_inventory_when_no_cameras_detected(monkeypatch):
    """No-camera startup should log inventory and keep webcam mode degraded without raising."""
    from threading import Event, RLock

    pytest.importorskip("flask")
    from modes.webcam import ConnectionTracker, FrameBuffer, StreamStats

    from pi_camera_in_docker import main

    cfg = {
        "mock_camera": False,
        "allow_pykms_mock": False,
        "resolution": (640, 480),
        "fps": 0,
        "jpeg_quality": 90,
        "target_fps": 0,
        "max_frame_age_seconds": 10.0,
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
        "camera_startup_error": None,
    }

    class FakePicamera2:
        pass

    class FakeJpegEncoder:
        def __init__(self, q):
            self.quality = q

    class FakeFileOutput:
        def __init__(self, out):
            self.output = out

    inventory = {
        "video_devices": ["/dev/video0"],
        "media_devices": ["/dev/media0"],
        "v4l_subdev_devices": ["/dev/v4l-subdev0"],
        "dma_heap_devices": ["/dev/dma_heap/system"],
        "vchiq_device": True,
    }

    error_calls = []

    def fake_error(msg, *args, **kwargs):
        error_calls.append((msg, kwargs))

    monkeypatch.setattr(main, "_check_device_availability", lambda _cfg: None)
    monkeypatch.setattr(
        main,
        "import_camera_components",
        lambda _allow: (FakePicamera2, FakeJpegEncoder, FakeFileOutput),
    )
    monkeypatch.setattr(main, "_detect_camera_devices", lambda: inventory)
    monkeypatch.setattr(main, "_get_camera_info", lambda _cls: ([], "test.path"))
    monkeypatch.setattr(main.logger, "error", fake_error)

    main._run_webcam_mode(state, cfg)

    assert state["recording_started"].is_set() is False
    startup_error = state["camera_startup_error"]
    assert startup_error is not None
    assert startup_error["code"] == "CAMERA_UNAVAILABLE"
    assert startup_error["reason"] == "camera_unavailable"

    assert error_calls
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
            "allow_pykms_mock": False,
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
            "allow_pykms_mock": False,
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


def test_run_webcam_mode_camera_detection_supports_both_global_camera_info_modes(monkeypatch):
    """Both camera-info discovery modes should reach camera setup without ImportError."""
    import importlib
    import sys
    import tempfile
    from threading import Event, RLock

    from modes.webcam import ConnectionTracker, FrameBuffer, StreamStats

    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("NODE_REGISTRY_PATH", f"{tmpdir}/registry.json")
        monkeypatch.setenv("MIO_APP_MODE", "management")
        monkeypatch.setenv("MIO_MOCK_CAMERA", "true")

        sys.modules.pop("main", None)
        main = importlib.import_module("pi_camera_in_docker.main")

        class FakePicamera2:
            started = False

            @staticmethod
            def global_camera_info():
                return [{"id": "camX"}]

            def __init__(self):
                self.configured = False
                self.recording_started = False

            def create_video_configuration(self, **kwargs):
                return kwargs

            def configure(self, config):
                self.configured = True

            def start_recording(self, encoder, output):
                self.recording_started = True
                self.started = True

        class FakeJpegEncoder:
            def __init__(self, q):
                self.quality = q

        class FakeFileOutput:
            def __init__(self, output):
                self.output = output

        cfg = {
            "mock_camera": False,
            "allow_pykms_mock": False,
            "resolution": (640, 480),
            "fps": 0,
            "jpeg_quality": 90,
            "target_fps": 0,
            "max_frame_age_seconds": 10.0,
            "max_stream_connections": 10,
        }

        for _mode in ("module_level", "class_fallback"):
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
            monkeypatch.setattr(
                main,
                "import_camera_components",
                lambda _allow: (FakePicamera2, FakeJpegEncoder, FakeFileOutput),
            )

            if _mode == "module_level":

                def get_camera_info_module(_cls):
                    return ([{"id": "cam0"}], "picamera2.global_camera_info")

                monkeypatch.setattr(
                    main,
                    "_get_camera_info",
                    get_camera_info_module,
                )
            else:

                def get_camera_info_class(_cls):
                    return ([{"id": "cam0"}], "Picamera2.global_camera_info")

                monkeypatch.setattr(
                    main,
                    "_get_camera_info",
                    get_camera_info_class,
                )

            main._run_webcam_mode(state, cfg)

            assert state["recording_started"].is_set()
            assert state["picam2_instance"] is not None

        sys.modules.pop("main", None)


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
        "allow_pykms_mock": False,
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
    from pi_camera_in_docker import main

    monkeypatch.setenv("MIO_APP_MODE", "webcam")
    monkeypatch.setenv("MIO_MOCK_CAMERA", "false")

    monkeypatch.setattr(main, "_run_webcam_mode", lambda _state, _cfg: None)

    app = main.create_webcam_app()
    app.motion_state["active_mock_fallback"] = True

    response = app.test_client().get("/api/config")

    assert response.status_code == 200
    runtime = response.get_json()["runtime"]
    assert runtime["mock_camera"] is False
    assert runtime["configured_mock_camera"] is False
    assert runtime["active_mock_fallback"] is True


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
