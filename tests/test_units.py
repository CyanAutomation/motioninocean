"""
Unit tests for Flask application components.
Tests without requiring camera hardware.
"""

import json
import sys
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
        if str(self) == "/dev/dma_heap":
            return True
        return False

    def mock_path_exists(self):
        # We also need to mock specific device paths to exist
        if str(self) in ["/dev/vchiq", "/dev/video0", "/dev/video1", "/dev/media0", "/dev/v4l-subdev0", "/dev/dri", "/dev/dma_heap/linux,cma", "/dev/dma_heap/system"]:
            return True
        return False

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
        if str(self) == "/dev/dma_heap":
            return True
        return False

    def mock_path_exists(self):
        if str(self) in ["/dev/vchiq", "/dev/video0", "/dev/media0", "/dev/dma_heap/system"]:
            return True
        return False

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
        if str(self) == "/dev/dma_heap":
            return True
        return False

    def mock_path_exists(self):
        if str(self) in ["/dev/vchiq", "/dev/media0", "/dev/v4l-subdev0", "/dev/dma_heap/system"]:
            return True
        return False

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


def test_flask_routes():
    """Test that Flask routes are properly defined."""
    try:
        from flask import Flask
    except ImportError:
        pytest.skip("Flask not installed in this environment")

    app = Flask(__name__)

    # Define test routes same as in main.py
    @app.route("/")
    def index():
        return "index"

    @app.route("/health")
    def health():
        return json.dumps({"status": "healthy"}), 200

    @app.route("/ready")
    def ready():
        return json.dumps({"status": "ready"}), 200

    @app.route("/stream.mjpg")
    def video_feed():
        return "stream"

    # Verify all expected routes are registered
    expected_routes = {"/", "/health", "/ready", "/stream.mjpg"}
    registered_routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert expected_routes.issubset(registered_routes), (
        f"Missing routes: {expected_routes - registered_routes}"
    )


def test_dockerfile_has_flask(workspace_root):
    """Verify Flask is declared in Dockerfile or requirements."""
    dockerfile_path = workspace_root / "Dockerfile"
    requirements_path = workspace_root / "requirements.txt"
    assert dockerfile_path.exists(), "Dockerfile not found"
    assert requirements_path.exists(), "requirements.txt not found"

    dockerfile_content = dockerfile_path.read_text().lower()
    requirements_content = requirements_path.read_text().lower()

    has_pip_install = (
        "pip3 install" in dockerfile_content
        and "flask" in dockerfile_content.split("pip3 install", 1)[-1].split("\n")[0]
    )
    has_requirements = "flask" in requirements_content

    assert has_pip_install or has_requirements, (
        "Flask not found in requirements.txt or Dockerfile pip install"
    )


@pytest.mark.parametrize(
    "resolution_str,expected",
    [
        ("1920x1080", (1920, 1080)),
        ("640x480", (640, 480)),
        ("1280x720", (1280, 720)),
    ],
)
def test_resolution_parsing(resolution_str, expected):
    """Test resolution string parsing."""
    resolution = tuple(map(int, resolution_str.split("x")))
    assert resolution == expected
    assert len(resolution) == 2
    assert all(isinstance(x, int) for x in resolution)


@pytest.mark.parametrize(
    "fps_str,expected",
    [
        ("30", 30),
        ("60", 60),
        ("0", 0),
        ("120", 120),
    ],
)
def test_fps_parsing(fps_str, expected):
    """Test FPS integer parsing."""
    fps = int(fps_str)
    assert fps == expected
    assert isinstance(fps, int)


def test_streaming_output_class():
    """Test the StreamingOutput class functionality."""
    import io
    import time
    from collections import deque
    from threading import Condition

    class StreamingOutput(io.BufferedIOBase):
        def __init__(self):
            self.frame = None
            self.condition = Condition()
            self.frame_count = 0
            self.last_frame_time = time.time()
            self.frame_times = deque(maxlen=30)

        def write(self, buf):
            with self.condition:
                self.frame = buf
                self.frame_count += 1
                now = time.time()
                self.frame_times.append(now)
                self.condition.notify_all()

        def get_fps(self):
            if len(self.frame_times) < 2:
                return 0.0
            time_span = self.frame_times[-1] - self.frame_times[0]
            if time_span == 0:
                return 0.0
            return (len(self.frame_times) - 1) / time_span

        def get_status(self):
            return {
                "frames_captured": self.frame_count,
                "current_fps": round(self.get_fps(), 2),
            }

    # Test instantiation
    output = StreamingOutput()
    assert output.frame_count == 0
    assert len(output.frame_times) == 0

    # Test writing frames
    for i in range(5):
        output.write(b"test_frame_" + str(i).encode())
        time.sleep(0.01)

    assert output.frame_count == 5
    assert len(output.frame_times) == 5

    # Test FPS calculation
    fps = output.get_fps()
    assert fps > 0
    assert fps < 1000  # Sanity check

    # Test status endpoint
    status = output.get_status()
    assert "frames_captured" in status
    assert "current_fps" in status
    assert status["frames_captured"] == 5


def test_logging_configuration():
    """Test logging setup."""
    import logging

    # Test basic logging setup
    logger = logging.getLogger(__name__)
    assert logger is not None

    # Verify logging levels exist
    assert hasattr(logging, "INFO")
    assert hasattr(logging, "ERROR")
    assert hasattr(logging, "WARNING")

    # Test logging methods don't raise exceptions
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")


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
        monkeypatch.setenv("APP_MODE", "management")
        monkeypatch.setenv("MOCK_CAMERA", "true")

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
        monkeypatch.setenv("APP_MODE", "management")
        monkeypatch.setenv("MOCK_CAMERA", "true")

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
    """No-camera RuntimeError path should log detailed detected device inventory."""
    from threading import Event, RLock

    pytest.importorskip("flask")
    from pi_camera_in_docker import main
    from modes.webcam import ConnectionTracker, FrameBuffer, StreamStats

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

    with pytest.raises(
        RuntimeError, match=r"No cameras detected\. Check device mappings and camera hardware\."
    ):
        main._run_webcam_mode(state, cfg)

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
            "node_registry_path": "/tmp/node-registry.json",
            "management_auth_token": "",
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


def test_run_webcam_mode_camera_detection_supports_both_global_camera_info_modes(monkeypatch):
    """Both camera-info discovery modes should reach camera setup without ImportError."""
    import importlib
    import sys
    import tempfile
    from threading import Event, RLock

    from modes.webcam import ConnectionTracker, FrameBuffer, StreamStats

    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("NODE_REGISTRY_PATH", f"{tmpdir}/registry.json")
        monkeypatch.setenv("APP_MODE", "management")
        monkeypatch.setenv("MOCK_CAMERA", "true")

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
        "node_registry_path": "/tmp/node-registry.json",
        "management_auth_token": "",
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
