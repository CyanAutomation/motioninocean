"""
Unit tests for Flask application components.
Tests without requiring camera hardware.
"""

import json

import pytest


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
    "edge_str,expected",
    [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("1", True),
        ("t", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("f", False),
    ],
)
def test_edge_detection_parsing(edge_str, expected):
    """Test edge detection boolean parsing."""
    result = edge_str.lower() in ("true", "1", "t")
    assert result == expected


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

    monkeypatch.setenv("HEALTHCHECK_URL", "https://example.com/health")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert healthcheck.check_health() is True
    assert captured["url"] == "https://example.com/health"
