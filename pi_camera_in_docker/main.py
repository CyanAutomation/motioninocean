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

# Import feature flags system
from feature_flags import FeatureFlags, get_feature_flags, is_flag_enabled
from flask import Flask, Response, jsonify, render_template, request
from flask_cors import CORS
from PIL import Image
from werkzeug.serving import make_server


LOG_LEVEL_EMOJI = {
    "DEBUG": "🐛",
    "INFO": "ℹ️",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "CRITICAL": "🔥",
}


class LogContextFilter(logging.Filter):
    """Inject emoji and event defaults into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.emoji = LOG_LEVEL_EMOJI.get(record.levelname, "")
        record.event = getattr(record, "event", "-")
        return True


# Configure structured logging early
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)s %(emoji)s | %(name)s | %(event)s | %(message)s")
)
handler.addFilter(LogContextFilter())
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [handler]
logger = logging.getLogger(__name__)


def log_event(level: int, event: str, message: str, **fields: object) -> None:
    """Log a message with a consistent event tag and optional key/value fields."""
    if fields:
        details = " ".join(f"{key}={value}" for key, value in fields.items())
        message = f"{message} | {details}"
    logger.log(level, message, extra={"event": event})


# Initialize and load feature flags early, before main configuration
feature_flags: FeatureFlags = get_feature_flags()
feature_flags.load()

# Check if debug logging should be enabled via feature flag
if is_flag_enabled("DEBUG_LOGGING"):
    root_logger.setLevel(logging.DEBUG)
    logger.debug("Debug logging enabled via MOTION_IN_OCEAN_DEBUG_LOGGING feature flag")
elif is_flag_enabled("TRACE_LOGGING"):
    root_logger.setLevel(logging.DEBUG)  # TRACE level would require custom implementation
    logger.debug("Trace logging enabled via MOTION_IN_OCEAN_TRACE_LOGGING feature flag")

# Log feature flags summary
log_event(logging.INFO, "startup", "Feature flags initialized", loaded_flags=len(feature_flags.get_all_flags()))

ALLOWED_APP_MODES = {"webcam_node", "management"}
DEFAULT_APP_MODE = "webcam_node"


PI3_PROFILE_DEFAULTS = {
    "RESOLUTION": "640x480",
    "FPS": "12",
    "JPEG_QUALITY": "75",
    "MAX_STREAM_CONNECTIONS": "3",
}


def _parse_bool_env(value: str) -> bool:
    """Parse common boolean environment variable values."""
    if not value:
        return False
    return value.lower().strip() in ("true", "1", "t", "yes", "on")


def _resolve_config_value(
    key: str,
    default: str,
    env: Optional[dict[str, str]] = None,
    profile_defaults: Optional[dict[str, str]] = None,
    profile_enabled: bool = False,
) -> str:
    """Resolve a config value, allowing profile defaults only when variable is absent."""
    env_values = os.environ if env is None else env
    defaults = PI3_PROFILE_DEFAULTS if profile_defaults is None else profile_defaults

    if key in env_values:
        return env_values[key]
    if profile_enabled and key in defaults:
        return defaults[key]
    return default


pi3_profile_env = os.environ.get("PI3_PROFILE")
motion_pi3_profile_env = os.environ.get("MOTION_IN_OCEAN_PI3_PROFILE")
pi3_profile_enabled = (
    is_flag_enabled("PI3_OPTIMIZATION")
    or (pi3_profile_env is not None and _parse_bool_env(pi3_profile_env))
    or (motion_pi3_profile_env is not None and _parse_bool_env(motion_pi3_profile_env))
)

app_mode_raw: str = os.environ.get("APP_MODE", DEFAULT_APP_MODE)
app_mode: str = app_mode_raw.strip().lower()
if app_mode not in ALLOWED_APP_MODES:
    allowed_values = ", ".join(sorted(ALLOWED_APP_MODES))
    log_event(
        logging.ERROR,
        "config",
        "Invalid APP_MODE value",
        app_mode=app_mode_raw,
        allowed_values=allowed_values,
    )
    raise ValueError(f"Invalid APP_MODE '{app_mode_raw}'. Allowed values: {allowed_values}")

camera_mode_enabled = app_mode == "webcam_node"
if camera_mode_enabled:
    log_event(logging.INFO, "config", "Camera mode enabled", app_mode=app_mode)
else:
    log_event(
        logging.INFO,
        "config",
        "Management mode enabled; camera initialization and camera endpoints are disabled",
        app_mode=app_mode,
    )

# Get configuration from environment variables
resolution_str: str = _resolve_config_value("RESOLUTION", "640x480", profile_enabled=pi3_profile_enabled)
fps_str: str = _resolve_config_value("FPS", "0", profile_enabled=pi3_profile_enabled)  # 0 = use camera default
target_fps_env = os.environ.get("TARGET_FPS")
target_fps_str: str = target_fps_env if target_fps_env is not None else fps_str
jpeg_quality_str: str = _resolve_config_value(
    "JPEG_QUALITY", "100", profile_enabled=pi3_profile_enabled
)
cors_origins_env_var = "MOTION_IN_OCEAN_CORS_ORIGINS"
cors_origins_str: Optional[str] = os.environ.get(cors_origins_env_var)
if cors_origins_str is None:
    cors_origins_env_var = "CORS_ORIGINS"
    cors_origins_str = os.environ.get(cors_origins_env_var)
max_frame_age_seconds_str: str = os.environ.get("MAX_FRAME_AGE_SECONDS", "10")
allow_pykms_mock_str: str = os.environ.get("ALLOW_PYKMS_MOCK", "false")
max_stream_connections_str: str = _resolve_config_value(
    "MAX_STREAM_CONNECTIONS", "10", profile_enabled=pi3_profile_enabled
)
max_frame_size_mb_str: str = os.environ.get("MAX_FRAME_SIZE_MB", "")  # Empty = auto-calculate

# Load feature flags (with backward compatibility for legacy env vars)
mock_camera: bool = is_flag_enabled("MOCK_CAMERA")
cors_enabled: bool = is_flag_enabled("CORS_SUPPORT")
allow_pykms_mock: bool = allow_pykms_mock_str.lower() in ("true", "1", "t")

log_event(logging.INFO, "config", "Feature flag values loaded", mock_camera=mock_camera, cors_enabled=cors_enabled)

if pi3_profile_enabled:
    log_event(
        logging.INFO,
        "startup",
        "Pi 3 profile active",
        resolution=resolution_str,
        fps=fps_str,
        target_fps=target_fps_str,
        jpeg_quality=jpeg_quality_str,
        max_stream_connections=max_stream_connections_str,
    )

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

if camera_mode_enabled and not mock_camera:
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
    from picamera2.encoders import JpegEncoder
    from picamera2.outputs import FileOutput
else:
    Picamera2 = None  # type: ignore[assignment]
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
# Only apply CORS if the CORS_SUPPORT feature flag is enabled
if cors_enabled:
    if cors_origins_str is None:
        cors_origins = ["*"]
    else:
        cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]
        if not cors_origins:
            logger.warning(
                f"{cors_origins_env_var} was set but empty. No origins will be allowed for CORS."
            )
    log_event(logging.INFO, "config", "CORS support enabled", origins=len(cors_origins))
else:
    cors_origins = []
    logger.info("CORS support disabled via MOTION_IN_OCEAN_CORS_SUPPORT feature flag")


def log_startup_summary() -> None:
    """Log a clear startup summary for Docker logs."""
    required_keys = [
        "max_frame_size_bytes",
        "mock_camera",
        "resolution",
        "fps",
        "target_fps",
        "jpeg_quality",
        "max_frame_age_seconds",
        "max_stream_connections",
        "cors_origins",
        "feature_flags",
    ]
    missing_keys = [key for key in required_keys if key not in globals() or globals()[key] is None]
    if missing_keys:
        missing_summary = ", ".join(missing_keys)
        logger.error(
            "Configuration variable not available during startup summary: %s", missing_summary
        )
        log_event(
            logging.ERROR,
            "startup",
            "Failed to log startup summary due to missing configuration variables",
            missing=missing_summary,
        )
        return

    max_frame_size_mb = (
        None if max_frame_size_bytes is None else round(max_frame_size_bytes / (1024 * 1024), 2)
    )

    # Get enabled feature flags count
    all_flags = feature_flags.get_all_flags()
    enabled_flags_count = sum(1 for v in all_flags.values() if v)

    log_event(
        logging.INFO,
        "startup",
        "Motion in Ocean configuration summary",
        mock_camera=mock_camera,
        resolution=f"{resolution[0]}x{resolution[1]}",
        fps=fps if fps > 0 else "default",
        target_fps=target_fps if target_fps > 0 else "disabled",
        jpeg_quality=jpeg_quality,
        max_frame_age_seconds=max_frame_age_seconds,
        max_stream_connections=max_stream_connections,
        max_frame_size_mb=max_frame_size_mb if max_frame_size_mb is not None else "auto",
        cors_origins=",".join(cors_origins) if cors_origins else "none",
        feature_flags_enabled=enabled_flags_count,
        feature_flags_total=len(all_flags),
    )


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

# Enable CORS for cross-origin access (dashboards, Home Assistant, etc.) if CORS support is enabled
if cors_enabled:
    CORS(app, resources={r"/*": {"origins": cors_origins}})
    logger.info(f"CORS enabled with origins: {cors_origins}")
else:
    logger.info("CORS disabled via MOTION_IN_OCEAN_CORS_SUPPORT feature flag")


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
    log_event(
        logging.INFO,
        "shutdown",
        "Received shutdown signal; setting shutdown flags.",
        signal=signum,
        timestamp=shutdown_timestamp,
    )
    # Only set atomic flags - don't perform cleanup in signal handler to avoid deadlocks
    recording_started.clear()
    shutdown_event.set()
    # Attempt to shutdown Flask server if it's running
    server = flask_server_state["server"]
    if server is not None:
        log_event(
            logging.INFO,
            "shutdown",
            "Shutting down Flask server...",
            timestamp=shutdown_timestamp,
        )
        try:
            server.shutdown()
            log_event(
                logging.INFO,
                "shutdown",
                "Flask server shutdown complete",
                timestamp=shutdown_timestamp,
            )
        except Exception as e:
            log_event(
                logging.WARNING,
                "shutdown",
                "Error shutting down Flask server",
                timestamp=shutdown_timestamp,
                error=e,
            )
    # Exit to trigger cleanup in main thread's finally block
    raise SystemExit(0)


@app.route("/")
def index() -> str:
    """Render main camera streaming page."""
    return render_template("index.html", width=resolution[0], height=resolution[1])


@app.route("/health")
def health() -> Tuple[Response, int]:
    """Health check endpoint - returns 200 if service is running."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat(), "app_mode": app_mode}), 200


@app.route("/ready")
def ready() -> Tuple[Response, int]:
    """Readiness probe - checks if camera is actually streaming."""
    if not camera_mode_enabled:
        return (
            jsonify(
                {
                    "status": "ready",
                    "reason": "camera_disabled_for_management_mode",
                    "timestamp": datetime.now().isoformat(),
                    "uptime_seconds": time.monotonic() - app.start_time_monotonic,
                    "app_mode": app_mode,
                }
            ),
            200,
        )

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
            "camera_mode_enabled": camera_mode_enabled,
            "app_mode": app_mode,
            "frames_captured": status["frames_captured"],
            "current_fps": status["current_fps"],
            "last_frame_age_seconds": status["last_frame_age_seconds"],
            "max_frame_age_seconds": max_frame_age_seconds,
            "uptime_seconds": round(uptime, 2),
            "resolution": status["resolution"],
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
                "app_mode": app_mode,
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


@app.route("/api/feature-flags")
def get_feature_flags_status() -> Tuple[Response, int]:
    """Feature flags endpoint - returns all feature flags and their current state.

    Returns current state of all feature flags, organized by category.
    Useful for debugging and understanding which experimental features are enabled.
    """
    try:
        flags_summary = feature_flags.get_summary()

        # Also include individual flag details with descriptions
        all_flags = {}
        for flag_name, flag in feature_flags._flags.items():
            all_flags[flag_name] = {
                "enabled": flag.enabled,
                "default": flag.default,
                "category": flag.category.value,
                "description": flag.description,
            }

        return jsonify(
            {
                "summary": flags_summary,
                "flags": all_flags,
                "timestamp": datetime.now().isoformat(),
            }
        ), 200
    except Exception as e:
        logger.error(f"Error retrieving feature flags status: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve feature flags"}), 500


def gen() -> Iterator[bytes]:
    """Generate MJPEG stream frames.

    Yields:
        MJPEG frame data with multipart boundaries
    """
    # Connection tracking moved to video_feed() to prevent race condition
    consecutive_timeouts = 0
    max_consecutive_timeouts = 3  # Exit after 3 consecutive timeouts (15 seconds)

    try:
        while True:
            # Check for shutdown signal
            if shutdown_event.is_set():
                log_event(logging.INFO, "stream", "Shutdown event set; ending MJPEG stream.")
                break

            if not recording_started.is_set():
                log_event(logging.INFO, "stream", "Recording not started; ending MJPEG stream.")
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
                        log_event(
                            logging.WARNING,
                            "stream",
                            "Stream timeout: no frames received. Camera may have stopped producing frames.",
                            timeout_seconds=consecutive_timeouts * 5,
                        )
                        break
                continue

            # Got a frame - reset timeout counter and update last frame time
            consecutive_timeouts = 0
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
    except Exception as e:
        logger.warning(f"Streaming client disconnected: {e}")
    finally:
        # Track disconnection - decrement counter
        current_connections = connection_tracker.decrement()
        log_event(
            logging.INFO,
            "stream",
            "Stream client disconnected.",
            active_connections=current_connections,
        )


def _build_stream_response() -> Response:
    """Create the MJPEG stream response with readiness and connection checks."""
    if not camera_mode_enabled:
        return Response("Camera endpoints are disabled in management mode.", status=404)

    if not recording_started.is_set():
        return Response("Camera stream not ready.", status=503)

    # Check connection limit and increment counter atomically to prevent race condition
    current_count = connection_tracker.get_count()
    if current_count >= max_stream_connections:
        log_event(
            logging.WARNING,
            "stream",
            "Stream connection rejected: connection limit reached.",
            max_connections=max_stream_connections,
            current_connections=current_count,
        )
        return Response(
            f"Maximum concurrent connections ({max_stream_connections}) reached. Try again later.",
            status=429,
        )

    # Increment counter
    current_connections = connection_tracker.increment()
    log_event(
        logging.INFO,
        "stream",
        "Stream client connected.",
        active_connections=current_connections,
    )

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


def _build_snapshot_response() -> Response:
    """Return the latest JPEG frame as a single-image snapshot."""
    if not camera_mode_enabled:
        return Response("Camera endpoints are disabled in management mode.", status=404)

    if not recording_started.is_set():
        return Response("Camera is not ready yet.", status=503)

    with output.condition:
        frame = output.frame
        if frame is None:
            return Response("No camera frame available yet.", status=503)

    if frame is None:
        return Response("No camera frame available yet.", status=503)

    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return Response(frame, mimetype="image/jpeg", headers=headers)


@app.route("/stream.mjpg")
def video_feed() -> Response:
    """Stream MJPEG video feed."""
    return _build_stream_response()


@app.route("/snapshot.jpg")
def snapshot() -> Response:
    """Return the latest camera frame as a JPEG image."""
    return _build_snapshot_response()


@app.route("/webcam/")
def octoprint_compat_webcam() -> Response:
    """OctoPrint-compatible webcam endpoint."""
    if not is_flag_enabled("OCTOPRINT_COMPATIBILITY"):
        return Response("OctoPrint compatibility routes are disabled.", status=404)

    action = request.args.get("action")
    if action is None:
        return Response("Missing required query parameter: action.", status=400)

    normalized_action = action.split("?", 1)[0].strip().lower()

    if normalized_action == "stream":
        return _build_stream_response()
    if normalized_action == "snapshot":
        return _build_snapshot_response()

    sanitized_action = action.replace("\r", "\\r").replace("\n", "\\n")
    return Response(
        f"Unsupported action: {sanitized_action!r}",
        status=400,
        mimetype="text/plain",
    )


def run_flask_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run Flask server in a separate thread using werkzeug's make_server.

    This allows the main thread to manage shutdown gracefully instead of
    being blocked by Flask's app.run() method.
    """
    log_event(
        logging.INFO,
        "server",
        "Creating Flask WSGI server.",
        host=host,
        port=port,
    )
    server = make_server(host, port, app, threaded=True)
    flask_server_state["server"] = server
    log_event(
        logging.INFO,
        "server",
        "Starting Flask WSGI server.",
        host=host,
        port=port,
    )
    server.serve_forever()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    log_startup_summary()
    picam2_instance = None
    if not camera_mode_enabled:
        try:
            log_event(
                logging.INFO,
                "startup",
                "Starting Flask server in management mode (camera disabled).",
                host="0.0.0.0",
                port=8000,
            )
            server = make_server("0.0.0.0", 8000, app, threaded=True)
            flask_server_state["server"] = server
            server.serve_forever()
            flask_thread.start()
            flask_thread.join()
        finally:
            recording_started.clear()
            log_event(logging.INFO, "shutdown", "Application shutdown complete.")

    elif mock_camera:
        log_event(
            logging.INFO,
            "startup",
            "MOCK_CAMERA enabled. Skipping Picamera2 initialization and generating dummy frames.",
        )
        # Create a dummy black image using Pillow
        fallback_image = Image.new("RGB", resolution, color=(0, 0, 0))
        fallback_buffer = io.BytesIO()
        fallback_image.save(fallback_buffer, format="JPEG", quality=jpeg_quality)
        dummy_image_jpeg = fallback_buffer.getvalue()

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
                log_event(logging.INFO, "mock_camera", "Mock frame generator stopped.")

        mock_thread: Thread = Thread(target=generate_mock_frames, daemon=True)
        mock_thread.start()

        # Wait for recording to start before Flask accepts requests
        log_event(logging.INFO, "mock_camera", "Waiting for mock camera to be ready...")
        recording_started.wait(timeout=5.0)
        if not recording_started.is_set():
            log_event(logging.ERROR, "mock_camera", "Mock camera failed to start within 5 seconds.")
            msg = "Mock camera initialization timeout"
            raise RuntimeError(msg)

        try:
            # Start the Flask app in a separate thread
            log_event(
                logging.INFO,
                "server",
                "Starting Flask server with mock camera.",
                host="0.0.0.0",
                port=8000,
            )
            flask_thread = Thread(target=run_flask_server, args=("0.0.0.0", 8000), daemon=False)
            flask_thread.start()
            # Main thread waits for Flask thread to complete
            flask_thread.join()
        finally:
            # Clean up mock thread on shutdown
            log_event(logging.INFO, "mock_camera", "Shutting down mock camera...")
            shutdown_event.set()
            mock_thread.join(timeout=5.0)
            if mock_thread.is_alive():
                log_event(
                    logging.WARNING,
                    "mock_camera",
                    "Mock thread did not stop within timeout; abandoning daemon thread.",
                    timeout_seconds=5,
                )
            recording_started.clear()
            log_event(logging.INFO, "mock_camera", "Mock camera shutdown complete.")

    else:
        try:
            log_event(logging.INFO, "camera", "Initializing Picamera2...")

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
                log_event(
                    logging.INFO,
                    "camera",
                    "Detected cameras.",
                    count=len(camera_info),
                    cameras=camera_info,
                )
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

            log_event(
                logging.INFO,
                "camera",
                "Configuring video stream.",
                resolution=f"{resolution[0]}x{resolution[1]}",
                format="BGR888",
                fps=fps if fps > 0 else "default",
            )
            # Configure for BGR format
            config_params = {"size": resolution, "format": "BGR888"}
            video_config = picam2_instance.create_video_configuration(main=config_params)
            picam2_instance.configure(video_config)

            log_event(logging.INFO, "camera", "Starting camera recording...")
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
                    log_event(
                        logging.INFO,
                        "camera",
                        "Applied FPS limit.",
                        fps=fps,
                        frame_duration_us=frame_duration_us,
                    )
                except Exception as e:
                    log_event(
                        logging.WARNING,
                        "camera",
                        "Failed to set FPS control; using camera default framerate.",
                        fps=fps,
                        error=e,
                    )

            # Mark recording as started only after start_recording succeeds
            recording_started.set()
            log_event(
                logging.INFO,
                "camera",
                "Camera recording started successfully.",
                jpeg_quality=jpeg_quality,
            )

            # Start the Flask app in a separate thread
            log_event(
                logging.INFO,
                "server",
                "Starting Flask server.",
                host="0.0.0.0",
                port=8000,
            )
            flask_thread = Thread(target=run_flask_server, args=("0.0.0.0", 8000), daemon=False)
            flask_thread.start()
            # Main thread waits for Flask thread to complete
            flask_thread.join()

        except PermissionError as e:
            log_event(
                logging.ERROR,
                "camera",
                "Permission denied accessing camera device.",
                error=e,
            )
            log_event(
                logging.ERROR,
                "camera",
                "Ensure the container has proper device access (--device mappings or --privileged).",
            )
            raise
        except RuntimeError as e:
            log_event(logging.ERROR, "camera", "Camera initialization failed.", error=e)
            log_event(
                logging.ERROR,
                "camera",
                "Verify camera is enabled on the host and working (rpicam-hello test).",
            )
            raise
        except Exception as e:
            log_event(
                logging.ERROR,
                "camera",
                "Unexpected error during initialization.",
                error=e,
            )
            logger.error("Unexpected error during initialization.", exc_info=True)
            raise
        finally:
            # Stop recording safely
            with picam2_lock:
                if picam2_instance is not None:
                    try:
                        if picam2_instance.started:
                            log_event(logging.INFO, "camera", "Stopping camera recording...")
                            picam2_instance.stop_recording()
                            log_event(logging.INFO, "camera", "Camera recording stopped.")
                    except Exception as e:
                        log_event(
                            logging.ERROR,
                            "camera",
                            "Error during camera shutdown.",
                            error=e,
                        )
                        logger.error("Error during camera shutdown.", exc_info=True)
            recording_started.clear()
            log_event(logging.INFO, "shutdown", "Application shutdown complete.")
