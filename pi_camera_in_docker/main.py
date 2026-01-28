#!/usr/bin/python3

import io
import logging
import os
import signal
import time
from collections import deque
from collections.abc import Iterator
from datetime import datetime
from threading import Condition, Event, Thread
from typing import Any, Dict, Optional, Tuple

import numpy as np
from flask import Flask, Response, jsonify, render_template, request
from flask_cors import CORS
from PIL import Image


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
cors_origins_env_var = "MOTION_IN_OCEAN_CORS_ORIGINS"
cors_origins_str: Optional[str] = os.environ.get(cors_origins_env_var)
if cors_origins_str is None:
    cors_origins_env_var = "CORS_ORIGINS"
    cors_origins_str = os.environ.get(cors_origins_env_var)
max_frame_age_seconds_str: str = os.environ.get("MAX_FRAME_AGE_SECONDS", "10")
allow_pykms_mock_str: str = os.environ.get("ALLOW_PYKMS_MOCK", "false")

mock_camera: bool = mock_camera_str.lower() in ("true", "1", "t")
allow_pykms_mock: bool = allow_pykms_mock_str.lower() in ("true", "1", "t")
logger.info(f"Mock camera enabled: {mock_camera}")
logger.info(f"Allow pykms mock: {allow_pykms_mock}")

if not mock_camera:
    # Workaround for pykms import error in headless container environments
    # picamera2 imports DrmPreview which requires pykms, but we don't use preview functionality
    try:
        from picamera2 import Picamera2
    except (ModuleNotFoundError, AttributeError) as e:
        if allow_pykms_mock and ("pykms" in str(e) or "kms" in str(e) or "PixelFormat" in str(e)):
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

            from picamera2 import Picamera2
        else:
            raise ImportError(
                "picamera2 import failed due to missing/incomplete DRM/KMS support. "
                "Install pykms or set ALLOW_PYKMS_MOCK=true to allow a mock module."
            ) from e
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
        logger.warning(
            f"{cors_origins_env_var} was set but empty. No origins will be allowed for CORS."
        )


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
    except Exception:
        logger.error("Edge detection processing failed.", exc_info=True)


class StreamStats:
    """Track streaming statistics separate from frame buffering."""

    def __init__(self) -> None:
        self._lock = Condition()
        self._frame_count: int = 0
        self._last_frame_monotonic: Optional[float] = None
        self._frame_times_monotonic: deque[float] = deque(maxlen=30)

    def record_frame(self, monotonic_timestamp: float) -> None:
        """Record a new frame timestamp from a monotonic clock."""
        with self._lock:
            self._frame_count += 1
            self._last_frame_monotonic = monotonic_timestamp
            self._frame_times_monotonic.append(monotonic_timestamp)

    def get_fps(self) -> float:
        """Calculate actual FPS from frame times."""
        with self._lock:
            frame_times = list(self._frame_times_monotonic)
        if len(frame_times) < 2:
            return 0.0
        time_span = frame_times[-1] - frame_times[0]
        if time_span == 0:
            return 0.0
        return (len(frame_times) - 1) / time_span

    def snapshot(self) -> Tuple[int, Optional[float], float]:
        """Return a snapshot of frame count, last frame time, and FPS."""
        with self._lock:
            frame_count = self._frame_count
            last_frame_time = self._last_frame_monotonic
            frame_times = list(self._frame_times_monotonic)
        
        # Calculate FPS outside lock using the snapshot
        if len(frame_times) < 2:
            current_fps = 0.0
        else:
            time_span = frame_times[-1] - frame_times[0]
            current_fps = 0.0 if time_span == 0 else (len(frame_times) - 1) / time_span
        
        return frame_count, last_frame_time, current_fps


class FrameBuffer(io.BufferedIOBase):
    """Thread-safe output handler for camera frames."""

    def __init__(self, stats: StreamStats) -> None:
        self.frame: Optional[bytes] = None
        self.condition: Condition = Condition()
        self._stats = stats

    def write(self, buf: bytes) -> int:
        """Write a new frame to the output buffer.

        Args:
            buf: JPEG-encoded frame data
        """
        with self.condition:
            self.frame = buf
            monotonic_now = time.monotonic()
            self._stats.record_frame(monotonic_now)
            self.condition.notify_all()
        return len(buf)


def get_stream_status(stats: StreamStats) -> Dict[str, Any]:
    """Return current streaming status with configuration details."""
    frame_count, last_frame_time, current_fps = stats.snapshot()
    last_frame_age_seconds = (
        None
        if last_frame_time is None
        else round(time.monotonic() - last_frame_time, 2)
    )
    return {
        "frames_captured": frame_count,
        "current_fps": round(current_fps, 2),
        "resolution": resolution,
        "edge_detection": edge_detection,
        "last_frame_age_seconds": last_frame_age_seconds,
    }


app = Flask(__name__, static_folder="static", static_url_path="/static")
no_cache_paths = {"/health", "/ready", "/metrics"}

# Security configuration
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", os.urandom(24).hex())
app.config["DEBUG"] = False

# Enable CORS for cross-origin access (dashboards, Home Assistant, etc.)
CORS(app, resources={r"/*": {"origins": cors_origins}})


@app.after_request
def add_no_cache_headers(response: Response) -> Response:
    """Ensure health and metrics endpoints are not cached."""
    if request.path in no_cache_paths:
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    return response

stream_stats = StreamStats()
output = FrameBuffer(stream_stats)
app.start_time = datetime.now()
picam2_instance: Optional[Any] = None  # Picamera2 instance (Optional since it may not be available)
recording_started = Event()  # Thread-safe flag to track if camera recording has started
shutdown_event = Event()


def handle_shutdown(signum: int, frame: Optional[object]) -> None:
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    logger.info(f"Received signal {signum}; shutting down.")
    recording_started.clear()
    shutdown_event.set()
    global picam2_instance
    if picam2_instance is not None:
        try:
            if picam2_instance.started:
                logger.info("Stopping camera recording due to shutdown signal...")
                picam2_instance.stop_recording()
                logger.info("Camera recording stopped")
        except Exception as e:
            logger.error(f"Error during camera shutdown: {e}", exc_info=True)
    raise SystemExit(0)


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
    status = get_stream_status(stream_stats)
    now = datetime.now()
    is_recording = recording_started.is_set()
    base_payload = {
        "timestamp": now.isoformat(),
        "uptime_seconds": (now - app.start_time).total_seconds(),
        "max_frame_age_seconds": max_frame_age_seconds,
        **status,
    }
    last_frame_age_seconds = base_payload["last_frame_age_seconds"]
    is_stale = (
        last_frame_age_seconds is not None
        and last_frame_age_seconds > max_frame_age_seconds
    )
    is_ready = is_recording and last_frame_age_seconds is not None and not is_stale
    if is_ready:
        readiness_status = "ready"
        reason = None
        status_code = 200
    else:
        readiness_status = "not_ready"
        if not is_recording:
            reason = "Camera not initialized or recording not started"
        elif last_frame_age_seconds is None:
            reason = "No frames captured yet"
        else:
            reason = "stale_stream"
        status_code = 503

    payload = {
        **base_payload,
        "status": readiness_status,
    }
    if reason is not None:
        payload["reason"] = reason

    return jsonify(payload), status_code


@app.route("/metrics")
def metrics() -> Tuple[Response, int]:
    """Metrics endpoint - returns camera metrics in JSON format for monitoring."""
    uptime = (datetime.now() - app.start_time).total_seconds()
    status = get_stream_status(stream_stats)

    return jsonify(
        {
            "camera_active": recording_started.is_set(),
            "frames_captured": status["frames_captured"],
            "current_fps": status["current_fps"],
            "last_frame_age_seconds": status["last_frame_age_seconds"],
            "max_frame_age_seconds": max_frame_age_seconds,
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
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
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
            fallback_image = Image.new("RGB", resolution, color=(0, 0, 0))
            fallback_buffer = io.BytesIO()
            fallback_image.save(fallback_buffer, format="JPEG", quality=jpeg_quality)
            dummy_image_jpeg = fallback_buffer.getvalue()
            logger.warning(
                "Mock camera: opencv not available, using Pillow to generate %sx%s JPEG fallback",
                resolution[0],
                resolution[1],
            )

        # Simulate camera streaming for the StreamingOutput
        def generate_mock_frames() -> None:
            """Generate mock camera frames for testing."""
            # Mark as started for mock mode using thread-safe Event
            recording_started.set()
            while not shutdown_event.is_set():
                time.sleep(1 / (fps if fps > 0 else 10))  # Simulate FPS
                output.write(dummy_image_jpeg)

        mock_thread: Thread = Thread(target=generate_mock_frames)
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
