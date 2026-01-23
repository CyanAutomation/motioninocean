#!/usr/bin/python3

import io
import logging
import os
import time
from collections import deque
from collections.abc import Iterator
from datetime import datetime
from threading import Condition, Event, Thread
from typing import Any, Dict, Optional, Tuple

import numpy as np
from flask import Flask, Response, jsonify, render_template
from flask_cors import CORS


# Optional opencv import - only needed for edge detection feature
try:
    import cv2

    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None  # type: ignore


# Configure structured logging early
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Get configuration from environment variables
resolution_str: str = os.environ.get("RESOLUTION", "640x480")
edge_detection_str: str = os.environ.get("EDGE_DETECTION", "false")
fps_str: str = os.environ.get("FPS", "0")  # 0 = use camera default
mock_camera_str: str = os.environ.get("MOCK_CAMERA", "false")
jpeg_quality_str: str = os.environ.get("JPEG_QUALITY", "100")
cors_origins_str: Optional[str] = os.environ.get("CORS_ORIGINS")
max_frame_age_seconds_str: str = os.environ.get("MAX_FRAME_AGE_SECONDS", "10")

mock_camera: bool = mock_camera_str.lower() in ("true", "1", "t")
logger.info(f"Mock camera enabled: {mock_camera}")

if not mock_camera:
    # Workaround for pykms import error in headless container environments
    # picamera2 imports DrmPreview which requires pykms, but we don't use preview functionality
    try:
        from picamera2 import Picamera2
    except (ModuleNotFoundError, AttributeError) as e:
        if "pykms" in str(e) or "kms" in str(e) or "PixelFormat" in str(e):
            # Mock the pykms module so picamera2 can import without DRM/KMS support
            import sys
            import types

            # Create mock modules with required attributes
            pykms_mock = types.ModuleType("pykms")
            kms_mock = types.ModuleType("kms")

            # Add PixelFormat mock class with common pixel formats
            # DrmPreview expects these attributes even though we don't use them
            class PixelFormatMock:
                RGB888 = "RGB888"
                XRGB8888 = "XRGB8888"
                BGR888 = "BGR888"
                XBGR8888 = "XBGR8888"

            pykms_mock.PixelFormat = PixelFormatMock
            kms_mock.PixelFormat = PixelFormatMock

            # Add to sys.modules to satisfy imports
            sys.modules["pykms"] = pykms_mock
            sys.modules["kms"] = kms_mock

            logger.warning(
                "pykms module not available or incomplete - using mock module. "
                "DrmPreview functionality disabled (not needed for headless streaming)."
            )

            # Retry import with mocked modules
            from picamera2 import Picamera2
        else:
            raise
    else:
        # Import succeeded on first try
        pass
    from picamera2.array import MappedArray
    from picamera2.encoders import JpegEncoder
    from picamera2.outputs import FileOutput
else:
    Picamera2 = None  # type: ignore[assignment]
    MappedArray = None  # type: ignore[assignment]
    JpegEncoder = None  # type: ignore[assignment]
    FileOutput = None  # type: ignore[assignment]

# Parse resolution
try:
    resolution: Tuple[int, int] = tuple(map(int, resolution_str.split("x")))  # type: ignore[assignment]
    # Validate resolution dimensions
    if len(resolution) != 2 or resolution[0] <= 0 or resolution[1] <= 0:
        logger.warning(f"Invalid RESOLUTION dimensions {resolution}. Using default 640x480.")
        resolution = (640, 480)
    elif resolution[0] > 4096 or resolution[1] > 4096:
        logger.warning(f"RESOLUTION {resolution} exceeds maximum 4096x4096. Using default 640x480.")
        resolution = (640, 480)
    else:
        logger.info(f"Camera resolution set to {resolution}")
except (ValueError, TypeError):
    logger.warning("Invalid RESOLUTION format. Using default 640x480.")
    resolution = (640, 480)

# Parse edge detection flag
edge_detection_requested: bool = edge_detection_str.lower() in ("true", "1", "t")

# Check if opencv is available for edge detection
if edge_detection_requested and not OPENCV_AVAILABLE:
    logger.warning(
        "Edge detection requested but opencv-python-headless is not installed. "
        "Edge detection will be disabled. To enable, rebuild with INCLUDE_OPENCV=true."
    )
    edge_detection = False
else:
    edge_detection = edge_detection_requested

logger.info(f"Edge detection: {edge_detection}")

# Parse max frame age for readiness
# Parse max frame age for readiness
max_frame_age_seconds: float = 10.0  # Initialize with default value
try:
    max_frame_age_seconds = float(max_frame_age_seconds_str)
    if max_frame_age_seconds <= 0:
        logger.warning(
            f"MAX_FRAME_AGE_SECONDS must be positive ({max_frame_age_seconds}). Using default 10."
        )
        max_frame_age_seconds = 10.0
    else:
        logger.info(f"Max frame age for readiness set to {max_frame_age_seconds} seconds")
except (ValueError, TypeError):
    logger.warning("Invalid MAX_FRAME_AGE_SECONDS format. Using default 10.")
    max_frame_age_seconds = 10.0

# Parse FPS
try:
    fps: int = int(fps_str)
    # Validate FPS value
    if fps < 0:
        logger.warning(f"FPS cannot be negative ({fps}). Using camera default.")
        fps = 0
    elif fps > 120:
        logger.warning(f"FPS {fps} exceeds recommended maximum of 120. Using 120.")
        fps = 120
    else:
        logger.info(f"Frame rate limited to {fps} FPS" if fps > 0 else "Using camera default FPS")
except (ValueError, TypeError):
    logger.warning("Invalid FPS format. Using camera default.")
    fps = 0

# Parse JPEG quality
try:
    jpeg_quality: int = int(jpeg_quality_str)
    # Validate JPEG quality value
    if jpeg_quality < 1 or jpeg_quality > 100:
        logger.warning(f"JPEG_QUALITY {jpeg_quality} out of range (1-100). Using default 100.")
        jpeg_quality = 100
    else:
        logger.info(f"JPEG quality set to {jpeg_quality}")
except (ValueError, TypeError):
    logger.warning("Invalid JPEG_QUALITY format. Using default 100.")
    jpeg_quality = 100

# Parse CORS origins (comma-separated). Default to wildcard only if not set.
if cors_origins_str is None:
    cors_origins = ["*"]
else:
    cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]
    if not cors_origins:
        logger.warning("CORS_ORIGINS was set but empty. No origins will be allowed for CORS.")


def apply_edge_detection(request: Any) -> None:
    """Apply edge detection filter to camera frame.

    Args:
        request: Camera frame request from picamera2
    """
    try:
        with MappedArray(request, "main") as m:
            # Convert to grayscale
            grey = cv2.cvtColor(m.array, cv2.COLOR_BGR2GRAY)
            # Apply Canny edge detection
            edges = cv2.Canny(grey, 100, 200)
            # Convert back to BGR so it can be encoded as JPEG
            edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            # Copy the result back to the mapped array
            np.copyto(m.array, edges_bgr)
    except Exception as e:
        logger.error(f"Edge detection processing failed: {e}", exc_info=True)


class StreamingOutput(io.BufferedIOBase):
    """Thread-safe output handler for camera frames."""

    def __init__(self) -> None:
        self.frame: Optional[bytes] = None
        self.condition: Condition = Condition()
        self.frame_count: int = 0
        self.last_frame_time: Optional[float] = None
        self.frame_times: deque[float] = deque(maxlen=30)  # Fixed-size deque prevents memory leak

    def write(self, buf: bytes) -> int:
        """Write a new frame to the output buffer.

        Args:
            buf: JPEG-encoded frame data
        """
        with self.condition:
            self.frame = buf
            self.frame_count += 1
            # Track frame timing for FPS calculation
            now = time.time()
            self.last_frame_time = now
            self.frame_times.append(now)  # deque automatically maintains maxlen=30
            self.condition.notify_all()
        return len(buf)

    def get_fps(self) -> float:
        """Calculate actual FPS from frame times.

        Returns:
            Current frames per second, or 0.0 if insufficient data
        """
        if len(self.frame_times) < 2:
            return 0.0
        time_span = self.frame_times[-1] - self.frame_times[0]
        if time_span == 0:
            return 0.0
        return (len(self.frame_times) - 1) / time_span

    def get_status(self) -> Dict[str, Any]:
        """Return current streaming status.

        Returns:
            Dictionary containing streaming statistics
        """
        last_frame_age_seconds = (
            None if self.last_frame_time is None else round(time.time() - self.last_frame_time, 2)
        )
        return {
            "frames_captured": self.frame_count,
            "current_fps": round(self.get_fps(), 2),
            "resolution": resolution,
            "edge_detection": edge_detection,
            "last_frame_age_seconds": last_frame_age_seconds,
        }


app = Flask(__name__, static_folder="static", static_url_path="/static")

# Security configuration
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", os.urandom(24).hex())
app.config["DEBUG"] = False

# Enable CORS for cross-origin access (dashboards, Home Assistant, etc.)
CORS(app, resources={r"/*": {"origins": cors_origins}})

output = StreamingOutput()
app.start_time = datetime.now()
picam2_instance: Optional[Any] = None  # Picamera2 instance (Optional since it may not be available)
recording_started = Event()  # Thread-safe flag to track if camera recording has started


@app.route("/")
def index() -> str:
    """Render main camera streaming page."""
    return render_template("index.html", width=resolution[0], height=resolution[1])


@app.route("/health")
def health() -> Tuple[Response, int]:
    """Health check endpoint - returns 200 if service is running."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200


@app.route("/ready")
def ready() -> Tuple[Response, int]:
    """Readiness probe - checks if camera is actually streaming."""
    if not recording_started.is_set():
        return jsonify(
            {
                "status": "not_ready",
                "reason": "Camera not initialized or recording not started",
                "timestamp": datetime.now().isoformat(),
            }
        ), 503

    status = output.get_status()
    last_frame_age_seconds = status["last_frame_age_seconds"]
    if last_frame_age_seconds is None:
        return jsonify(
            {
                "status": "not_ready",
                "reason": "No frames captured yet",
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - app.start_time).total_seconds(),
                "max_frame_age_seconds": max_frame_age_seconds,
                **status,
            }
        ), 503

    if last_frame_age_seconds > max_frame_age_seconds:
        return jsonify(
            {
                "status": "not_ready",
                "reason": "stale_stream",
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - app.start_time).total_seconds(),
                "max_frame_age_seconds": max_frame_age_seconds,
                **status,
            }
        ), 503

    return jsonify(
        {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - app.start_time).total_seconds(),
            "max_frame_age_seconds": max_frame_age_seconds,
            **status,
        }
    ), 200


@app.route("/metrics")
def metrics() -> Tuple[Response, int]:
    """Metrics endpoint - returns camera metrics in JSON format for monitoring."""
    uptime = (datetime.now() - app.start_time).total_seconds()
    status = output.get_status()

    return jsonify(
        {
            "camera_active": recording_started.is_set(),
            "frames_captured": status["frames_captured"],
            "current_fps": status["current_fps"],
            "last_frame_age_seconds": status["last_frame_age_seconds"],
            "uptime_seconds": round(uptime, 2),
            "resolution": status["resolution"],
            "edge_detection": status["edge_detection"],
            "timestamp": datetime.now().isoformat(),
        }
    ), 200


def gen() -> Iterator[bytes]:
    """Generate MJPEG stream frames.

    Yields:
        MJPEG frame data with multipart boundaries
    """
    try:
        while True:
            if not recording_started.is_set():
                logger.info("Recording not started; ending MJPEG stream.")
                break
            with output.condition:
                output.condition.wait(timeout=5.0)
                frame = output.frame
            # Skip if frame is not yet available
            if frame is None:
                continue
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
    except Exception as e:
        logger.warning(f"Streaming client disconnected: {e}")


@app.route("/stream.mjpg")
def video_feed() -> Response:
    """Stream MJPEG video feed."""
    if not recording_started.is_set():
        return Response("Camera stream not ready.", status=503)
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "X-Accel-Buffering": "no",
    }
    return Response(
        gen(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers=headers,
    )


if __name__ == "__main__":
    picam2_instance = None
    if mock_camera:
        logger.info(
            "MOCK_CAMERA enabled. Skipping Picamera2 initialization and generating dummy frames."
        )
        # Create a dummy black image
        dummy_image = np.zeros((resolution[1], resolution[0], 3), dtype=np.uint8)
        if OPENCV_AVAILABLE:
            dummy_image_jpeg = cv2.imencode(".jpg", dummy_image)[1].tobytes()
        else:
            # Fallback: create minimal JPEG without opencv
            # Minimal valid JPEG: black 1x1 image
            dummy_image_jpeg = (
                b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
                b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
                b"\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c"
                b"\x1c $.'\" ,#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08"
                b"\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01"
                b"\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06"
                b"\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05"
                b"\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa"
                b'\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17'
                b"\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85"
                b"\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5"
                b"\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5"
                b"\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4"
                b"\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda"
                b"\x00\x08\x01\x01\x00\x00?\x00\xfe\xfe\xa2\x8a(\xff\xd9"
            )
            logger.warning("Mock camera: opencv not available, using minimal JPEG placeholder")

        # Simulate camera streaming for the StreamingOutput
        def generate_mock_frames() -> None:
            """Generate mock camera frames for testing."""
            # Mark as started for mock mode using thread-safe Event
            recording_started.set()
            while True:
                time.sleep(1 / (fps if fps > 0 else 10))  # Simulate FPS
                output.write(dummy_image_jpeg)

        import threading

        mock_thread: Thread = threading.Thread(target=generate_mock_frames)
        mock_thread.daemon = True
        mock_thread.start()

        # Start the Flask app
        logger.info("Starting Flask server on 0.0.0.0:8000 with mock camera.")
        app.run(host="0.0.0.0", port=8000, threaded=True)

    else:
        try:
            logger.info("Initializing Picamera2...")
            picam2_instance = Picamera2()

            logger.info(
                f"Configuring video: resolution={resolution}, format=BGR888, fps={fps if fps > 0 else 'default'}"
            )
            # Configure for BGR format for opencv
            config_params = {"size": resolution, "format": "BGR888"}
            if fps > 0:
                config_params["framerate"] = fps
            video_config = picam2_instance.create_video_configuration(main=config_params)
            picam2_instance.configure(video_config)

            if edge_detection:
                logger.info("Enabling edge detection preprocessing")
                picam2_instance.pre_callback = apply_edge_detection

            logger.info("Starting camera recording...")
            # Start recording with configured JPEG quality
            picam2_instance.start_recording(JpegEncoder(q=jpeg_quality), FileOutput(output))

            # Mark recording as started only after start_recording succeeds
            recording_started.set()
            logger.info(f"Camera recording started successfully (JPEG quality: {jpeg_quality})")

            # Start the Flask app
            logger.info("Starting Flask server on 0.0.0.0:8000")
            app.run(host="0.0.0.0", port=8000, threaded=True)

        except PermissionError as e:
            logger.error(f"Permission denied accessing camera device: {e}")
            logger.error(
                "Ensure the container has proper device access (--device mappings or --privileged)"
            )
            raise
        except RuntimeError as e:
            logger.error(f"Camera initialization failed: {e}")
            logger.error("Verify camera is enabled on the host and working (rpicam-hello test)")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {e}", exc_info=True)
            raise
        finally:
            # Stop recording safely
            if picam2_instance is not None:
                try:
                    if picam2_instance.started:
                        logger.info("Stopping camera recording...")
                        picam2_instance.stop_recording()
                        logger.info("Camera recording stopped")
                except Exception as e:
                    logger.error(f"Error during camera shutdown: {e}", exc_info=True)
            recording_started.clear()
            logger.info("Application shutdown complete")
