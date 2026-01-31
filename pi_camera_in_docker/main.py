#!/usr/bin/python3

import io
import logging
import os
import signal
import time
from collections import deque
from collections.abc import Iterator
from datetime import datetime
from threading import Condition, Event, Lock, Thread
from typing import Any, Dict, Optional, Tuple

import numpy as np
from flask import Flask, Response, jsonify, render_template, request
from flask_cors import CORS
from PIL import Image
from werkzeug.serving import make_server


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
target_fps_env = os.environ.get("TARGET_FPS")
target_fps_str: str = target_fps_env if target_fps_env is not None else fps_str
mock_camera_str: str = os.environ.get("MOCK_CAMERA", "false")
jpeg_quality_str: str = os.environ.get("JPEG_QUALITY", "100")
cors_origins_env_var = "MOTION_IN_OCEAN_CORS_ORIGINS"
cors_origins_str: Optional[str] = os.environ.get(cors_origins_env_var)
if cors_origins_str is None:
    cors_origins_env_var = "CORS_ORIGINS"
    cors_origins_str = os.environ.get(cors_origins_env_var)
max_frame_age_seconds_str: str = os.environ.get("MAX_FRAME_AGE_SECONDS", "10")
allow_pykms_mock_str: str = os.environ.get("ALLOW_PYKMS_MOCK", "false")
max_stream_connections_str: str = os.environ.get("MAX_STREAM_CONNECTIONS", "10")
max_frame_size_mb_str: str = os.environ.get("MAX_FRAME_SIZE_MB", "")  # Empty = auto-calculate

mock_camera: bool = mock_camera_str.lower() in ("true", "1", "t")
allow_pykms_mock: bool = allow_pykms_mock_str.lower() in ("true", "1", "t")
logger.info(f"Mock camera enabled: {mock_camera}")
logger.info(f"Allow pykms mock: {allow_pykms_mock}")

# Parse max stream connections
try:
    max_stream_connections: int = int(max_stream_connections_str)
    if max_stream_connections < 1:
        logger.warning(
            f"MAX_STREAM_CONNECTIONS must be positive ({max_stream_connections}). Using default 10."
        )
        max_stream_connections = 10
    elif max_stream_connections > 100:
        logger.warning(
            f"MAX_STREAM_CONNECTIONS {max_stream_connections} exceeds maximum 100. Using 100."
        )
        max_stream_connections = 100
    else:
        logger.info(f"Max concurrent stream connections set to {max_stream_connections}")
except (ValueError, TypeError):
    logger.warning("Invalid MAX_STREAM_CONNECTIONS format. Using default 10.")
    max_stream_connections = 10

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
            msg = (
                "picamera2 import failed due to missing/incomplete DRM/KMS support. "
                "Install pykms or set ALLOW_PYKMS_MOCK=true to allow a mock module."
            )
            raise ImportError(msg) from e
    try:
        from picamera2.array import MappedArray
    except ModuleNotFoundError:
        try:
            from picamera2 import MappedArray  # type: ignore[attr-defined]
        except (ModuleNotFoundError, AttributeError) as e:
            msg = (
                "picamera2 MappedArray import failed. The installed picamera2 package "
                "is missing the array module or MappedArray export. "
                "Install a newer picamera2 build (python3-picamera2) that includes it."
            )
            raise ImportError(msg) from e
    from picamera2.encoders import JpegEncoder
    from picamera2.outputs import FileOutput
else:
    Picamera2 = None  # type: ignore[assignment]
    MappedArray = None  # type: ignore[assignment]
    JpegEncoder = None  # type: ignore[assignment]
    FileOutput = None  # type: ignore[assignment]


# Parse resolution
def _parse_resolution(resolution_str: str) -> Tuple[int, int]:
    """Parse resolution string and return validated dimensions."""
    parts = resolution_str.split("x")
    if len(parts) != 2:
        msg = f"Invalid resolution format: expected WIDTHxHEIGHT, got '{resolution_str}'"
        raise ValueError(msg)
    return int(parts[0]), int(parts[1])


try:
    width, height = _parse_resolution(resolution_str)

    # Validate resolution dimensions
    if width <= 0 or height <= 0:
        logger.warning(f"Invalid RESOLUTION dimensions {width}x{height}. Using default 640x480.")
        resolution = (640, 480)
    elif width > 4096 or height > 4096:
        logger.warning(
            f"RESOLUTION {width}x{height} exceeds maximum 4096x4096. Using default 640x480."
        )
        resolution = (640, 480)
    else:
        resolution = (width, height)
        logger.info(f"Camera resolution set to {resolution}")
except (ValueError, TypeError) as e:
    logger.warning(f"Invalid RESOLUTION format '{resolution_str}': {e}. Using default 640x480.")
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
    # Validate FPS value - Raspberry Pi cameras typically max out around 40-60 FPS
    if fps < 0:
        logger.warning(f"FPS cannot be negative ({fps}). Using camera default.")
        fps = 0
    elif fps > 60:
        logger.warning(
            f"FPS {fps} exceeds recommended maximum of 60 for Raspberry Pi cameras. Using 60."
        )
        fps = 60
    else:
        logger.info(f"Frame rate limited to {fps} FPS" if fps > 0 else "Using camera default FPS")
except (ValueError, TypeError):
    logger.warning("Invalid FPS format. Using camera default.")
    fps = 0

# Parse target FPS throttle
try:
    target_fps: int = int(target_fps_str)
    if target_fps < 0:
        logger.warning(f"TARGET_FPS cannot be negative ({target_fps}). Disabling throttle.")
        target_fps = 0
    elif target_fps > 60:
        logger.warning(f"TARGET_FPS {target_fps} exceeds recommended maximum of 60. Using 60.")
        target_fps = 60
    elif target_fps > 0:
        source = "TARGET_FPS" if target_fps_env is not None else "FPS"
        logger.info(f"Target FPS throttle set to {target_fps} FPS (from {source})")
    else:
        logger.info("Target FPS throttle disabled")
except (ValueError, TypeError):
    logger.warning("Invalid TARGET_FPS format. Target FPS throttle disabled.")
    target_fps = 0

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

# Calculate maximum frame size based on resolution and quality
# Formula: width * height * 3 (BGR) * compression_ratio (JPEG quality dependent)
# Higher quality = less compression = larger files
# Typical JPEG compression ratios: quality 100 ~= 0.3, quality 85 ~= 0.1, quality 50 ~= 0.05
if max_frame_size_mb_str:
    try:
        max_frame_size_mb = float(max_frame_size_mb_str)
        if max_frame_size_mb <= 0:
            logger.warning(f"MAX_FRAME_SIZE_MB must be positive ({max_frame_size_mb}). Using auto.")
            max_frame_size_bytes: Optional[int] = None
        else:
            max_frame_size_bytes = int(max_frame_size_mb * 1024 * 1024)
            logger.info(
                f"Max frame size set to {max_frame_size_mb} MB ({max_frame_size_bytes} bytes)"
            )
    except (ValueError, TypeError):
        logger.warning("Invalid MAX_FRAME_SIZE_MB format. Using auto-calculated limit.")
        max_frame_size_bytes = None
else:
    # Auto-calculate based on resolution and quality
    # Worst case: uncompressed would be width * height * 3 bytes
    # JPEG at quality 100 typically achieves 30-40% compression
    # Use 50% as conservative estimate for max size
    width, height = resolution
    uncompressed_size = width * height * 3
    compression_factor = 0.5 if jpeg_quality >= 90 else 0.3 if jpeg_quality >= 70 else 0.2
    max_frame_size_bytes = int(uncompressed_size * compression_factor)
    logger.info(
        f"Auto-calculated max frame size: {max_frame_size_bytes / (1024 * 1024):.2f} MB "
        f"(resolution: {width}x{height}, quality: {jpeg_quality})"
    )

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
    except Exception as e:
        logger.error("Edge detection processing failed: %s", e, exc_info=True)
        # Return without modifying the frame to avoid corrupted output
        # The original frame will be encoded instead
        return


class StreamStats:
    """Track streaming statistics separate from frame buffering."""

    def __init__(self) -> None:
        self._lock = Lock()
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

    def __init__(
        self,
        stats: StreamStats,
        max_frame_size: Optional[int] = None,
        target_fps: int = 0,
    ) -> None:
        self.frame: Optional[bytes] = None
        self.condition: Condition = Condition()
        self._stats = stats
        self._max_frame_size = max_frame_size
        self._target_frame_interval = None
        if target_fps > 0:
            self._target_frame_interval = 1.0 / target_fps
        self._last_frame_monotonic: Optional[float] = None
        self._dropped_frames = 0

    def write(self, buf: bytes) -> int:
        """Write a new frame to the output buffer.

        Args:
            buf: JPEG-encoded frame data

        Returns:
            Number of bytes written

        Raises:
            ValueError: If frame size exceeds maximum allowed size
        """
        frame_size = len(buf)

        # Validate frame size to prevent memory exhaustion
        if self._max_frame_size is not None and frame_size > self._max_frame_size:
            self._dropped_frames += 1
            logger.warning(
                f"Dropped frame: size {frame_size} bytes exceeds maximum {self._max_frame_size} bytes "
                f"(total dropped: {self._dropped_frames})"
            )
            # Return the size to satisfy encoder interface, but don't store the frame
            return frame_size

        with self.condition:
            monotonic_now = time.monotonic()
            if (
                self._target_frame_interval is not None
                and self._last_frame_monotonic is not None
                and monotonic_now - self._last_frame_monotonic < self._target_frame_interval
            ):
                self._dropped_frames += 1
                logger.debug(
                    "Dropped frame due to target FPS throttle (total dropped: %s)",
                    self._dropped_frames,
                )
                return frame_size
            self.frame = buf
            self._last_frame_monotonic = monotonic_now
            self._stats.record_frame(monotonic_now)
            self.condition.notify_all()
        return frame_size

    def get_dropped_frames(self) -> int:
        """Return the number of dropped frames due to size limits or throttling."""
        return self._dropped_frames


def get_stream_status(stats: StreamStats) -> Dict[str, Any]:
    """Return current streaming status with configuration details."""
    # Capture current time first for consistent age calculation
    current_time = time.monotonic()
    frame_count, last_frame_time, current_fps = stats.snapshot()
    # Use the captured time for age calculation to ensure consistency
    last_frame_age_seconds = (
        None if last_frame_time is None else round(current_time - last_frame_time, 2)
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

# Security configuration - use env var or generate a persistent key
# Note: In production with sessions, SECRET_KEY should be set via FLASK_SECRET_KEY env var
# If not set, we generate a deterministic key based on container hostname to persist across restarts
secret_key = os.environ.get("FLASK_SECRET_KEY")
if secret_key is None:
    # Generate a deterministic key from hostname (persists in same container)
    # This is a reasonable default for internal networks without authentication
    import socket

    hostname = socket.gethostname()
    secret_key = f"motion-in-ocean-{hostname}".encode().hex()
    logger.warning(
        "FLASK_SECRET_KEY not set. Using hostname-based key. "
        "Set FLASK_SECRET_KEY environment variable for production deployments with sessions."
    )
app.config["SECRET_KEY"] = secret_key
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
output = FrameBuffer(
    stream_stats,
    max_frame_size=max_frame_size_bytes,
    target_fps=target_fps,
)
app.start_time_monotonic = time.monotonic()  # Use monotonic clock for uptime calculations
picam2_instance: Optional[Any] = None  # Picamera2 instance (Optional since it may not be available)
picam2_lock = Lock()  # Lock for thread-safe access to picam2_instance
recording_started = Event()  # Thread-safe flag to track if camera recording has started
shutdown_event = Event()
flask_server_state = {"server": None}  # Flask WSGI server instance for explicit shutdown


# Connection tracking for stream endpoint
class ConnectionTracker:
    """Thread-safe connection counter."""

    def __init__(self) -> None:
        self._count = 0
        self._lock = Lock()

    def increment(self) -> int:
        """Increment counter and return new value."""
        with self._lock:
            self._count += 1
            return self._count

    def decrement(self) -> int:
        """Decrement counter and return new value."""
        with self._lock:
            self._count -= 1
            return self._count

    def get_count(self) -> int:
        """Get current count."""
        with self._lock:
            return self._count


connection_tracker = ConnectionTracker()


def handle_shutdown(signum: int, _frame: Optional[object]) -> None:
    """Handle SIGTERM/SIGINT for graceful shutdown.

    Signal handlers should only set atomic flags to avoid deadlocks.
    Actual cleanup is performed in the main thread's finally block.
    """
    shutdown_timestamp = datetime.now().isoformat()
    logger.info(f"[{shutdown_timestamp}] Received signal {signum}; setting shutdown flags.")
    # Only set atomic flags - don't perform cleanup in signal handler to avoid deadlocks
    recording_started.clear()
    shutdown_event.set()
    # Attempt to shutdown Flask server if it's running
    flask_server = flask_server_state["server"]
    if flask_server is not None:
        logger.info(f"[{shutdown_timestamp}] Shutting down Flask server...")
        try:
            flask_server.shutdown()
            logger.info(f"[{shutdown_timestamp}] Flask server shutdown complete")
        except Exception as e:
            logger.warning(f"[{shutdown_timestamp}] Error shutting down Flask server: {e}")
    # Exit to trigger cleanup in main thread's finally block
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
    # Capture camera state first for consistency
    is_recording = recording_started.is_set()
    status = get_stream_status(stream_stats)
    now = datetime.now()
    uptime_seconds = time.monotonic() - app.start_time_monotonic
    base_payload = {
        "timestamp": now.isoformat(),
        "uptime_seconds": uptime_seconds,
        "max_frame_age_seconds": max_frame_age_seconds,
        **status,
    }
    last_frame_age_seconds = base_payload["last_frame_age_seconds"]
    is_stale = last_frame_age_seconds is not None and last_frame_age_seconds > max_frame_age_seconds
    # Check recording state captured at the start for consistency
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
    uptime = time.monotonic() - app.start_time_monotonic
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


@app.route("/api/config")
def get_config() -> Tuple[Response, int]:
    """Configuration endpoint - returns all application configuration settings.

    Returns current environment-based configuration and runtime settings.
    Useful for UI dashboards and monitoring tools to display app configuration.
    """
    uptime = time.monotonic() - app.start_time_monotonic

    return jsonify(
        {
            "camera_settings": {
                "resolution": list(resolution),  # Convert tuple to list for JSON
                "fps": fps,
                "target_fps": target_fps,
                "jpeg_quality": jpeg_quality,
                "edge_detection": edge_detection,
                "opencv_available": OPENCV_AVAILABLE,
            },
            "stream_control": {
                "max_stream_connections": max_stream_connections,
                "max_frame_age_seconds": max_frame_age_seconds,
                "cors_origins": cors_origins,
                "current_stream_connections": connection_tracker.get_count(),
            },
            "runtime": {
                "camera_active": recording_started.is_set(),
                "uptime_seconds": round(uptime, 2),
                "mock_camera": mock_camera,
            },
            "limits": {
                "max_resolution": [4096, 4096],
                "max_fps": 60,
                "max_jpeg_quality": 100,
                "min_jpeg_quality": 1,
            },
            "timestamp": datetime.now().isoformat(),
        }
    ), 200


def gen() -> Iterator[bytes]:
    """Generate MJPEG stream frames.

    Yields:
        MJPEG frame data with multipart boundaries
    """
    # Connection tracking moved to video_feed() to prevent race condition
    consecutive_timeouts = 0
    max_consecutive_timeouts = 3  # Exit after 3 consecutive timeouts (15 seconds)
    time.monotonic()

    try:
        while True:
            # Check for shutdown signal
            if shutdown_event.is_set():
                logger.info("Shutdown event set; ending MJPEG stream.")
                break

            if not recording_started.is_set():
                logger.info("Recording not started; ending MJPEG stream.")
                break

            wait_start = time.monotonic()
            with output.condition:
                output.condition.wait(timeout=5.0)
                frame = output.frame

            # Check actual condition: did we get a frame?
            # Don't rely solely on wait() return value due to spurious wakeups
            if frame is None:
                # No frame available - check if we actually timed out
                elapsed = time.monotonic() - wait_start
                if elapsed >= 4.5:  # Allow some margin for timeout detection
                    consecutive_timeouts += 1
                    if consecutive_timeouts >= max_consecutive_timeouts:
                        logger.warning(
                            f"Stream timeout: no frames received for {consecutive_timeouts * 5} seconds. "
                            "Camera may have stopped producing frames."
                        )
                        break
                continue

            # Got a frame - reset timeout counter and update last frame time
            consecutive_timeouts = 0
            time.monotonic()
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
    except Exception as e:
        logger.warning(f"Streaming client disconnected: {e}")
    finally:
        # Track disconnection - decrement counter
        current_connections = connection_tracker.decrement()
        logger.info(f"Stream client disconnected. Active connections: {current_connections}")


@app.route("/stream.mjpg")
def video_feed() -> Response:
    """Stream MJPEG video feed."""
    if not recording_started.is_set():
        return Response("Camera stream not ready.", status=503)

    # Check connection limit and increment counter atomically to prevent race condition
    current_count = connection_tracker.get_count()
    if current_count >= max_stream_connections:
        logger.warning(
            f"Stream connection rejected: limit of {max_stream_connections} reached "
            f"(current: {current_count})"
        )
        return Response(
            f"Maximum concurrent connections ({max_stream_connections}) reached. Try again later.",
            status=429,
        )

    # Increment counter
    current_connections = connection_tracker.increment()
    logger.info(f"Stream client connected. Active connections: {current_connections}")

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


def run_flask_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run Flask server in a separate thread using werkzeug's make_server.

    This allows the main thread to manage shutdown gracefully instead of
    being blocked by Flask's app.run() method.
    """
    logger.info(f"Creating Flask WSGI server on {host}:{port}")
    flask_server = make_server(host, port, app, threaded=True)
    flask_server_state["server"] = flask_server
    logger.info(f"Starting Flask WSGI server on {host}:{port}")
    flask_server.serve_forever()


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
            try:
                while not shutdown_event.is_set():
                    time.sleep(1 / (fps if fps > 0 else 10))  # Simulate FPS
                    output.write(dummy_image_jpeg)
            finally:
                logger.info("Mock frame generator stopped")

        mock_thread: Thread = Thread(target=generate_mock_frames, daemon=True)
        mock_thread.start()

        # Wait for recording to start before Flask accepts requests
        logger.info("Waiting for mock camera to be ready...")
        recording_started.wait(timeout=5.0)
        if not recording_started.is_set():
            logger.error("Mock camera failed to start within 5 seconds")
            msg = "Mock camera initialization timeout"
            raise RuntimeError(msg)

        try:
            # Start the Flask app in a separate thread
            logger.info("Starting Flask server on 0.0.0.0:8000 with mock camera.")
            flask_thread = Thread(target=run_flask_server, args=("0.0.0.0", 8000), daemon=False)
            flask_thread.start()
            # Main thread waits for Flask thread to complete
            flask_thread.join()
        finally:
            # Clean up mock thread on shutdown
            logger.info("Shutting down mock camera...")
            shutdown_event.set()
            mock_thread.join(timeout=5.0)
            if mock_thread.is_alive():
                logger.warning(
                    "Mock thread did not stop within 5 seconds timeout. "
                    "Thread will be abandoned as daemon (auto-terminated on exit)."
                )
            recording_started.clear()
            logger.info("Mock camera shutdown complete")

    else:
        try:
            logger.info("Initializing Picamera2...")

            # Check if cameras are available before initializing
            try:
                camera_info = Picamera2.global_camera_info()
                if not camera_info:
                    error_msg = (
                        "No cameras detected by Picamera2. "
                        "Ensure the camera is enabled on the host (raspi-config) and "
                        "proper device mappings are configured in docker-compose.yaml. "
                        "Required devices typically include: /dev/video*, /dev/media*, /dev/vchiq, /dev/dma_heap. "
                        "Run 'detect-devices.sh' to identify required devices for your hardware."
                    )
                    raise RuntimeError(error_msg)
                logger.info(f"Detected {len(camera_info)} camera(s): {camera_info}")
            except IndexError as e:
                # This shouldn't happen with the check above, but handle it defensively
                error_msg = (
                    "Camera detection failed with IndexError. "
                    "No cameras are available to Picamera2. "
                    "Verify camera hardware is connected and enabled, and that the container has "
                    "proper device access (--device mappings for /dev/video*, /dev/media*, etc.)."
                )
                raise RuntimeError(error_msg) from e

            picam2_instance = Picamera2()

            logger.info(
                f"Configuring video: resolution={resolution}, format=BGR888, fps={fps if fps > 0 else 'default'}"
            )
            # Configure for BGR format for opencv
            config_params = {"size": resolution, "format": "BGR888"}
            video_config = picam2_instance.create_video_configuration(main=config_params)
            picam2_instance.configure(video_config)

            if edge_detection:
                logger.info("Enabling edge detection preprocessing")
                picam2_instance.pre_callback = apply_edge_detection

            logger.info("Starting camera recording...")
            # Start recording with configured JPEG quality
            picam2_instance.start_recording(JpegEncoder(q=jpeg_quality), FileOutput(output))

            # Apply FPS limit via camera controls if specified
            if fps > 0:
                try:
                    # FrameDurationLimits expects microseconds per frame
                    frame_duration_us = int(1_000_000 / fps)
                    picam2_instance.set_controls(
                        {"FrameDurationLimits": (frame_duration_us, frame_duration_us)}
                    )
                    logger.info(
                        f"Applied FPS limit: {fps} FPS (frame duration: {frame_duration_us} µs)"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to set FPS control to {fps}: {e}. Using camera default framerate."
                    )

            # Mark recording as started only after start_recording succeeds
            recording_started.set()
            logger.info(f"Camera recording started successfully (JPEG quality: {jpeg_quality})")

            # Start the Flask app in a separate thread
            logger.info("Starting Flask server on 0.0.0.0:8000")
            flask_thread = Thread(target=run_flask_server, args=("0.0.0.0", 8000), daemon=False)
            flask_thread.start()
            # Main thread waits for Flask thread to complete
            flask_thread.join()

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
            with picam2_lock:
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
