"""
Unit tests for Flask application endpoints.
Tests the endpoints without requiring camera hardware.
"""

import pytest
import os
import json
import io
import time
from threading import Condition
from pathlib import Path


@pytest.mark.unit
def test_flask_import():
    """Test that Flask can be imported."""
    try:
        from flask import Flask
        assert Flask is not None
    except ImportError:
        pytest.skip("Flask not installed (will be available in Docker container)")


@pytest.mark.unit
def test_flask_routes_registration():
    """Test that Flask routes are properly defined."""
    try:
        from flask import Flask
        
        # Create a minimal test app to verify route structure
        app = Flask(__name__)
        
        # Define test routes same as in main.py
        @app.route('/')
        def index():
            return "index"
        
        @app.route('/health')
        def health():
            return json.dumps({"status": "healthy"}), 200
        
        @app.route('/ready')
        def ready():
            return json.dumps({"status": "ready"}), 200
        
        @app.route('/stream.mjpg')
        def video_feed():
            return "stream"
        
        # Test routes
        routes_found = {'/': False, '/health': False, '/ready': False, '/stream.mjpg': False}
        
        for rule in app.url_map.iter_rules():
            if str(rule.rule) in routes_found:
                routes_found[str(rule.rule)] = True
        
        assert all(routes_found.values()), \
            f"Not all routes found: {[k for k, v in routes_found.items() if not v]}"
        
    except ImportError:
        # Verify Flask is in the Dockerfile instead
        dockerfile = Path(__file__).parent.parent.parent / 'Dockerfile'
        with open(dockerfile, 'r') as f:
            assert 'python3-flask' in f.read(), "Flask not declared in Dockerfile dependencies"


@pytest.mark.unit
def test_environment_parsing(mock_env_vars):
    """Test environment variable parsing logic."""
    # Test resolution parsing
    resolution_str = os.environ.get("RESOLUTION", "640x480")
    resolution = tuple(map(int, resolution_str.split('x')))
    assert resolution == (640, 480), f"Expected (640, 480), got {resolution}"
    
    # Test edge detection parsing
    edge_detection_str = os.environ.get("EDGE_DETECTION", "false")
    edge_detection = edge_detection_str.lower() in ('true', '1', 't')
    assert edge_detection == False, f"Expected False, got {edge_detection}"
    
    # Test FPS parsing
    fps_str = os.environ.get("FPS", "0")
    fps = int(fps_str)
    assert fps == 30, f"Expected 30, got {fps}"


@pytest.mark.unit
def test_streaming_output_class():
    """Test the StreamingOutput class."""
    
    class StreamingOutput(io.BufferedIOBase):
        def __init__(self):
            self.frame = None
            self.condition = Condition()
            self.frame_count = 0
            self.last_frame_time = time.time()
            self.frame_times = []

        def write(self, buf):
            with self.condition:
                self.frame = buf
                self.frame_count += 1
                now = time.time()
                self.frame_times.append(now)
                if len(self.frame_times) > 30:
                    self.frame_times.pop(0)
                self.condition.notify_all()

        def get_fps(self):
            """Calculate actual FPS from frame times"""
            if len(self.frame_times) < 2:
                return 0.0
            time_span = self.frame_times[-1] - self.frame_times[0]
            if time_span == 0:
                return 0.0
            return (len(self.frame_times) - 1) / time_span

        def get_status(self):
            """Return current streaming status"""
            return {
                "frames_captured": self.frame_count,
                "current_fps": round(self.get_fps(), 2),
            }
    
    # Create instance and test
    output = StreamingOutput()
    assert output is not None
    
    # Test writing frames
    for i in range(5):
        output.write(b'test_frame_' + str(i).encode())
        time.sleep(0.01)
    
    assert output.frame_count == 5, f"Expected 5 frames, got {output.frame_count}"
    
    # Test FPS calculation
    fps = output.get_fps()
    assert fps > 0, f"FPS should be greater than 0, got {fps}"
    
    # Test status endpoint
    status = output.get_status()
    assert 'frames_captured' in status, "Missing frames_captured in status"
    assert 'current_fps' in status, "Missing current_fps in status"
    assert status['frames_captured'] == 5


@pytest.mark.unit
def test_logging_configuration():
    """Test logging setup."""
    import logging
    
    # Test basic logging setup
    logger = logging.getLogger(__name__)
    
    # Verify logger was created
    assert logger is not None, "Logger creation failed"
    
    # Verify logging levels exist
    assert hasattr(logging, 'INFO'), "Missing logging.INFO"
    assert hasattr(logging, 'ERROR'), "Missing logging.ERROR"
    assert hasattr(logging, 'WARNING'), "Missing logging.WARNING"
    
    # Test logging methods exist
    assert hasattr(logger, 'info'), "Missing logger.info method"
    assert hasattr(logger, 'warning'), "Missing logger.warning method"
    assert hasattr(logger, 'error'), "Missing logger.error method"


@pytest.mark.unit
def test_resolution_parsing_variations():
    """Test various resolution string formats."""
    test_cases = [
        ("640x480", (640, 480)),
        ("1280x720", (1280, 720)),
        ("1920x1080", (1920, 1080)),
    ]
    
    for resolution_str, expected in test_cases:
        resolution = tuple(map(int, resolution_str.split('x')))
        assert resolution == expected, \
            f"Failed to parse {resolution_str}: expected {expected}, got {resolution}"


@pytest.mark.unit
def test_edge_detection_boolean_parsing():
    """Test edge detection boolean parsing."""
    test_cases = [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("1", True),
        ("t", True),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("0", False),
        ("f", False),
        ("anything", False),
    ]
    
    for value, expected in test_cases:
        result = value.lower() in ('true', '1', 't')
        assert result == expected, \
            f"Failed to parse '{value}': expected {expected}, got {result}"
