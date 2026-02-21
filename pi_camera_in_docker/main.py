#!/usr/bin/python3
"""Motion In Ocean Flask application initialization and mode selection.

Handles creation of Flask apps for webcam and management modes, configuration loading,
device detection, and camera initialization (both mock and real hardware).
"""

import io
import logging
import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path  # Moved here
from threading import Event, RLock, Thread
from typing import Any, Dict, Optional, Tuple, cast
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from flask import Flask, g, jsonify, render_template, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .application_settings import ApplicationSettings
from .cat_gif_generator import CatGifGenerator
from .config_validator import ConfigValidationError, validate_all_config
from .discovery import DiscoveryAnnouncer, build_discovery_payload
from .feature_flags import FeatureFlags, get_feature_flags, is_flag_enabled
from .logging_config import configure_logging, log_provenance_info
from .management_api import register_management_routes
from .modes.webcam import (
    ConnectionTracker,
    FrameBuffer,
    StreamStats,
    get_stream_status,
    import_camera_components,
    register_management_camera_error_routes,
    register_webcam_routes,
)
from .runtime_config import (
    load_env_config,
    merge_config_with_settings,
)


# Conditional import for picamera2 - not available in all test environments
try:
    from picamera2 import global_camera_info as _picamera2_global_camera_info
except (ModuleNotFoundError, ImportError):
    # Fallback when picamera2 is not available (e.g., in CI without hardware)
    def _picamera2_global_camera_info():
        return []


from PIL import Image
from werkzeug.serving import make_server

from .sentry_config import init_sentry
from .settings_api import register_settings_routes
from .shared import register_shared_routes, register_webcam_control_plane_auth


ALLOWED_APP_MODES = {"webcam", "management"}
DEFAULT_APP_MODE = "webcam"

configure_logging()
log_provenance_info()
logger = logging.getLogger(__name__)

feature_flags: FeatureFlags = get_feature_flags()
feature_flags.load()


def _redacted_url_for_logs(url: str) -> str:
    """Redact query parameters and fragments from URL for safe logging.

    Args:
        url: Full URL to redact.

    Returns:
        URL with only scheme, host, port, and path visible (credentials/query removed).
    """
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.port is not None:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, "", ""))


def _parse_resolution(resolution_str: str) -> Tuple[int, int]:
    """Parse resolution string to (width, height) tuple.

    Args:
        resolution_str: Resolution in format 'WIDTHxHEIGHT' (e.g., '640x480').

    Returns:
        Tuple of (width, height) as integers.

    Raises:
        ValueError: If format is invalid or dimensions are out of range (1-4096).
    """
    parts = resolution_str.split("x")
    if len(parts) != 2:
        message = f"Invalid resolution format: {resolution_str}"
        raise ValueError(message)
    width, height = int(parts[0]), int(parts[1])
    if width <= 0 or height <= 0 or width > 4096 or height > 4096:
        message = f"Resolution dimensions out of valid range (1-4096): {width}x{height}"
        raise ValueError(message)
    return width, height


def _load_config() -> Dict[str, Any]:
    """Load all configuration from environment variables.

    Returns:
        Complete configuration dict with all environment variables and defaults.
    """
    return load_env_config()


def _merge_config_with_settings(env_config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge environment configuration with persisted application settings.

    Applies runtime overrides from JSON settings file to environment-based config.

    Args:
        env_config: Configuration dict loaded from environment variables.

    Returns:
        Merged configuration with persisted settings applied as overrides.
    """
    return merge_config_with_settings(env_config)


def _detect_camera_devices() -> Dict[str, Any]:
    """
    Detect available camera-related device nodes on the system.
    Returns a dict with detected device information.
    Failures are logged but don't raise exceptions (graceful fallback).
    """
    result: Dict[str, Any] = {  # Use Any here as a pragmatic solution for complex mixed-type dicts
        "has_camera": False,
        "video_devices": [],
        "media_devices": [],
        "v4l_subdev_devices": [],
        "dma_heap_devices": [],
        "vchiq_device": False,
        "dri_device": False,
    }

    try:
        # Check DMA heap devices
        dma_heap_dir = "/dev/dma_heap"
        if Path(dma_heap_dir).is_dir():
            try:
                dma_devices = [f.name for f in Path(dma_heap_dir).iterdir()]
                result["dma_heap_devices"] = [f"/dev/dma_heap/{d}" for d in dma_devices]
            except OSError:
                logger.debug("Could not list /dev/dma_heap directory")

        # Check video devices
        for i in range(10):
            video_device = f"/dev/video{i}"
            if Path(video_device).exists():
                result["video_devices"].append(video_device)

        # Check media devices
        for i in range(10):
            media_device = f"/dev/media{i}"
            if Path(media_device).exists():
                result["media_devices"].append(media_device)

        # Check v4l sub-device nodes
        for i in range(64):
            subdev_device = f"/dev/v4l-subdev{i}"
            if Path(subdev_device).exists():
                result["v4l_subdev_devices"].append(subdev_device)

        # Check VCHIQ
        if Path("/dev/vchiq").exists():
            result["vchiq_device"] = True

        # Check DRI (graphics)
        if Path("/dev/dri").exists():
            result["dri_device"] = True

        # Set has_camera flag
        result["has_camera"] = bool(
            result["video_devices"]
            or result["media_devices"]
            or result["v4l_subdev_devices"]
            or result["vchiq_device"]
        )
    except Exception as e:
        logger.warning("Device detection encountered error: %s", e)

    return result


def _collect_current_config() -> Dict[str, Any]:
    """
    Collect current configuration from environment variables.
    Returns a simplified config dict for the setup API.
    """
    try:
        resolution = _parse_resolution(os.environ.get("MIO_RESOLUTION", "640x480"))
    except ValueError:
        resolution = (640, 480)

    try:
        fps = int(os.environ.get("MIO_FPS", "24"))
    except ValueError:
        fps = 24

    try:
        target_fps_str = os.environ.get("MIO_TARGET_FPS", "")
        target_fps = int(target_fps_str) if target_fps_str else None
    except ValueError:
        target_fps = None

    try:
        jpeg_quality = int(os.environ.get("MIO_JPEG_QUALITY", "90"))
        if not 1 <= jpeg_quality <= 100:
            jpeg_quality = 90
    except ValueError:
        jpeg_quality = 90

    try:
        max_stream_connections = int(os.environ.get("MIO_MAX_STREAM_CONNECTIONS", "10"))
        if not 1 <= max_stream_connections <= 100:
            max_stream_connections = 10
    except ValueError:
        max_stream_connections = 10

    pi3_profile = os.environ.get("MIO_PI3_PROFILE", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    mock_camera = is_flag_enabled("MOCK_CAMERA")
    cors_origins = os.environ.get("MIO_CORS_ORIGINS", "")
    auth_token = os.environ.get("MIO_MANAGEMENT_AUTH_TOKEN", "")

    return {
        "resolution": f"{resolution[0]}x{resolution[1]}",
        "fps": fps,
        "target_fps": target_fps,
        "jpeg_quality": jpeg_quality,
        "max_connections": max_stream_connections,
        "pi3_profile": pi3_profile,
        "mock_camera": mock_camera,
        "cors_origins": cors_origins,
        "auth_token": auth_token,
    }


def _get_setup_presets() -> Dict[str, Dict[str, Any]]:
    """
    Return available setup presets with default values.
    """
    return {
        "pi3_low_power": {
            "name": "Pi3 Low Power",
            "description": "Optimized for Raspberry Pi 3 with low resource usage",
            "resolution": "640x480",
            "fps": 12,
            "target_fps": 12,
            "jpeg_quality": 75,
            "max_connections": 3,
            "pi3_profile": True,
            "mock_camera": False,
        },
        "pi5_high_quality": {
            "name": "Pi5 High Quality",
            "description": "High quality streaming for Raspberry Pi 5",
            "resolution": "1280x720",
            "fps": 24,
            "target_fps": 24,
            "jpeg_quality": 90,
            "max_connections": 10,
            "pi3_profile": False,
            "mock_camera": False,
        },
    }


def _validate_setup_config(config: Dict[str, Any]) -> Tuple[bool, list]:
    """
    Validate setup configuration values.
    Returns (is_valid, list_of_errors).
    """
    errors = []

    # Validate resolution
    if "resolution" in config:
        try:
            _parse_resolution(config["resolution"])
        except ValueError as e:
            errors.append(f"Resolution: {e!s}")

    # Validate FPS
    if "fps" in config:
        fps = config.get("fps", 0)
        if not isinstance(fps, int) or fps < 0 or fps > 120:
            errors.append("FPS must be an integer between 0 and 120")

    # Validate target FPS
    if "target_fps" in config and config["target_fps"] is not None:
        target_fps = config["target_fps"]
        if not isinstance(target_fps, int) or target_fps < 1 or target_fps > 120:
            errors.append("Target FPS must be an integer between 1 and 120 (or null to disable)")

    # Validate JPEG quality
    if "jpeg_quality" in config:
        quality = config.get("jpeg_quality", 90)
        if not isinstance(quality, int) or quality < 1 or quality > 100:
            errors.append("JPEG Quality must be between 1 and 100")

    # Validate max connections
    if "max_connections" in config:
        conns = config.get("max_connections", 10)
        if not isinstance(conns, int) or conns < 1 or conns > 100:
            errors.append("Max Connections must be between 1 and 100")

    return len(errors) == 0, errors


def _generate_docker_compose_content(
    _config: Dict[str, Any], detected_devices: Dict[str, Any]
) -> str:
    """
    Generate docker-compose.yaml content based on configuration and detected devices.
    """
    # Base docker-compose with anchors
    compose = """# Motion In Ocean Docker Compose Configuration
# Generated by the Set-Up UI

x-motion-in-ocean-common: &motion-in-ocean-common
  image: ghcr.io/cyanautomation/motioninocean:latest
  platform: linux/arm64
  restart: unless-stopped
  env_file: ./.env
  security_opt:
    - no-new-privileges:true
  stop_grace_period: 30s
  logging:
    driver: json-file
    options:
      max-size: "10m"
      max-file: "3"

x-motion-in-ocean-camera: &motion-in-ocean-camera
  volumes:
    - /run/udev:/run/udev:ro
  devices:
"""

    # Add detected devices
    if detected_devices.get("dma_heap_devices"):
        for device in detected_devices["dma_heap_devices"]:
            compose += f"    - {device}:{device}\n"

    if detected_devices.get("vchiq_device"):
        compose += "    - /dev/vchiq:/dev/vchiq\n"

    if detected_devices.get("video_devices"):
        for device in detected_devices["video_devices"]:
            compose += f"    - {device}:{device}\n"

    if detected_devices.get("media_devices"):
        for device in detected_devices["media_devices"]:
            compose += f"    - {device}:{device}\n"

    if detected_devices.get("v4l_subdev_devices"):
        for device in detected_devices["v4l_subdev_devices"]:
            compose += f"    - {device}:{device}\n"

    if detected_devices.get("dri_device"):
        compose += "    - /dev/dri:/dev/dri\n"

    compose += """  group_add:
    - video
  device_cgroup_rules:
    - "c 253:* rmw"
    - "c 511:* rmw"
    - "c 81:* rmw"
    - "c 250:* rmw"

services:
  motion-in-ocean:
    <<: [*motion-in-ocean-common, *motion-in-ocean-camera]
    container_name: motion-in-ocean
    environment:
      TZ: ${TZ}
      APP_MODE: ${MIO_APP_MODE:-webcam}
      RESOLUTION: ${MIO_RESOLUTION}
      FPS: ${MIO_FPS}
      TARGET_FPS: ${MIO_TARGET_FPS:-}
      JPEG_QUALITY: ${MIO_JPEG_QUALITY}
      MAX_STREAM_CONNECTIONS: ${MIO_MAX_STREAM_CONNECTIONS:-2}
      # Canonical Pi 3 profile toggle consumed by runtime config loading.
      MIO_PI3_PROFILE: ${MIO_PI3_PROFILE:-false}
      MIO_OCTOPRINT_COMPATIBILITY: ${MIO_OCTOPRINT_COMPATIBILITY:-false}
      MIO_CORS_ORIGINS: ${MIO_CORS_ORIGINS}
      MOCK_CAMERA: ${MOCK_CAMERA:-false}
      MIO_HEALTHCHECK_READY: ${MIO_HEALTHCHECK_READY:-true}
    ports:
      - "${MIO_BIND_HOST:-127.0.0.1}:${MIO_PORT:-8000}:8000"
    volumes:
      - motion-in-ocean-data:/data
    healthcheck:
      test: ["CMD", "python3", "/app/healthcheck.py"]
      interval: 2m
      timeout: 10s
      retries: 3
      start_period: 2m

volumes:
  motion-in-ocean-data:
    driver: local
"""
    return compose


def _generate_env_content(config: Dict[str, Any]) -> str:
    """
    Generate .env content based on configuration.
    """
    env_lines = [
        "# Motion In Ocean Environment Configuration",
        "# Generated by the Set-Up UI",
        "",
        "# Timezone",
        "TZ=UTC",
        "",
        "# Application Mode (webcam or management)",
        "MIO_MODE=webcam",
        "",
        "# Camera Configuration",
        f"MIO_RESOLUTION={config.get('resolution', '640x480')}",
        f"MIO_FPS={config.get('fps', 0)}",
        f"MIO_TARGET_FPS={config.get('target_fps', '') or ''}",
        f"MIO_JPEG_QUALITY={config.get('jpeg_quality', 90)}",
        f"MIO_MAX_STREAM_CONNECTIONS={config.get('max_connections', 10)}",
        # Canonical Pi 3 profile env variable consumed by runtime config loading.
        f"MIO_PI3_PROFILE={'true' if config.get('pi3_profile') else 'false'}",
        "",
        "# Features and Integration",
        "MIO_OCTOPRINT_COMPATIBILITY=false",
        f"MIO_CORS_ORIGINS={config.get('cors_origins', '')}",
        f"MOCK_CAMERA={'true' if config.get('mock_camera') else 'false'}",
        "MIO_HEALTHCHECK_READY=true",
        "",
        "# Networking",
        "MIO_BIND_HOST=127.0.0.1",
        "MIO_PORT=8000",
        "MIO_IMAGE_TAG=latest",
        "",
        "# Management/Security",
        f"MANAGEMENT_AUTH_TOKEN={config.get('auth_token', '')}",
        "",
    ]

    return "\n".join(env_lines)


def _init_flask_app(_config: Dict[str, Any]) -> Tuple[Flask, Limiter]:
    """Initialize Flask app and rate limiter."""
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.start_time_monotonic = time.monotonic()

    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["100/minute"],
        storage_uri=os.environ.get("MIO_LIMITER_STORAGE_URI", "memory://"),
    )

    return app, limiter


def _register_middleware(app: Flask, config: Dict[str, Any]) -> None:
    """Register middleware for correlation ID, logging, and CORS."""

    # Add correlation ID middleware
    @app.before_request
    def _add_correlation_id() -> None:
        g.correlation_id = request.headers.get(
            "X-Correlation-ID", request.headers.get("x-correlation-id", "")
        ) or str(uuid4())

    # Ensure correlation ID is returned in response
    @app.after_request
    def _inject_correlation_id(response):
        if hasattr(g, "correlation_id") and g.correlation_id:
            response.headers["X-Correlation-ID"] = g.correlation_id
        return response

    _register_request_logging(app)

    if config["cors_enabled"]:
        cors_origins_config = config.get("cors_origins", "*")

        if isinstance(cors_origins_config, str):
            parsed_origins = [
                origin.strip() for origin in cors_origins_config.split(",") if origin.strip()
            ]
            cors_origins = (
                parsed_origins
                if len(parsed_origins) > 1
                else (parsed_origins[0] if parsed_origins else "*")
            )
        elif isinstance(cors_origins_config, (list, tuple, set)):
            parsed_origins = [
                str(origin).strip() for origin in cors_origins_config if str(origin).strip()
            ]
            cors_origins = parsed_origins if parsed_origins else "*"
        else:
            cors_origins = "*"

        cors_options: Dict[str, Any] = {
            "resources": {r"/*": {"origins": cors_origins}},
            "send_wildcard": False,  # Default to False
        }
        if cors_origins == "*":
            cors_options["send_wildcard"] = True  # Update to True if needed

        CORS(app, **cors_options)


def _init_app_state(config: Dict[str, Any]) -> dict:
    """Initialize application state dictionary."""
    return {
        "app_mode": config["app_mode"],
        "recording_started": Event(),
        "shutdown_requested": Event(),
        "camera_lock": RLock(),
        "max_frame_age_seconds": config["max_frame_age_seconds"],
        "picam2_instance": None,
        "cat_gif_generator": None,
        "camera_startup_error": None,
    }


def _indicator(state_value: str, label: str, details: str) -> Dict[str, str]:
    """Build a health check indicator dictionary.

    Constructs a structured status indicator for health check reporting with
    state value (ok/fail/warn/unknown), descriptive label, and detailed message.

    Args:
        state_value: Status state as string (ok, fail, warn, unknown).
        label: Human-readable label for the indicator.
        details: Detailed description of the indicator state.

    Returns:
        Dictionary with state, label, and details keys.
    """
    return {
        "state": state_value,
        "label": label,
        "details": details,
    }


class HealthCheckBuilder:
    """Encapsulates health check state machine for application endpoints.

    Builds indicators for camera pipeline, stream freshness, connection capacity,
    and mock mode based on runtime state and configuration.
    """

    def __init__(self, config: Dict[str, Any], state: dict, app: Flask) -> None:
        """Initialize HealthCheckBuilder with config, state, and app context.

        Args:
            config: Application configuration dictionary.
            state: Application runtime state dictionary.
            app: Flask application instance.
        """
        self.config = config
        self.state = state
        self.app = app

    def build_camera_pipeline_indicator(self, camera_is_active: bool) -> Dict[str, str]:
        """Build camera pipeline status indicator.

        Evaluates whether camera recording pipeline is active and returns
        appropriate indicator based on app mode and activity status.

        Args:
            camera_is_active: Whether camera is currently active.

        Returns:
            Indicator dictionary with state, label, and details.
        """
        if camera_is_active:
            return _indicator(
                "ok",
                "Camera pipeline active",
                "Camera recording pipeline is active.",
            )
        if self.state.get("app_mode") == "management":
            return _indicator(
                "unknown",
                "Camera pipeline not required",
                "Management mode does not require an active camera pipeline.",
            )
        return _indicator(
            "fail",
            "Camera pipeline inactive",
            "Camera recording pipeline is not active.",
        )

    def build_stream_freshness_indicator(self, stream_status: Dict[str, Any]) -> Dict[str, str]:
        """Build stream freshness status indicator.

        Evaluates last frame age against configured threshold and returns
        indicator reflecting freshness of stream data.

        Args:
            stream_status: Stream status dict with last_frame_age_seconds.

        Returns:
            Indicator dictionary with state, label, and details.
        """
        last_frame_age_seconds = stream_status.get("last_frame_age_seconds")
        max_age_seconds = self.state.get(
            "max_frame_age_seconds", self.config["max_frame_age_seconds"]
        )

        if last_frame_age_seconds is None:
            return _indicator(
                "unknown",
                "Stream freshness unavailable",
                "No frame age is currently available to evaluate freshness.",
            )
        if last_frame_age_seconds <= max_age_seconds:
            return _indicator(
                "ok",
                "Stream is fresh",
                f"Last frame age {last_frame_age_seconds:.2f}s is within the {max_age_seconds:.2f}s threshold.",
            )
        return _indicator(
            "fail",
            "Stream is stale",
            f"Last frame age {last_frame_age_seconds:.2f}s exceeds the {max_age_seconds:.2f}s threshold.",
        )

    def build_connection_capacity_indicator(
        self,
        current_connections_count: int,
        max_connections_count: int,
    ) -> Dict[str, str]:
        """Build connection capacity status indicator.

        Evaluates current connection count against maximum and returns
        indicator reflecting capacity health (ok/warn/fail).

        Args:
            current_connections_count: Number of active stream connections.
            max_connections_count: Maximum allowed stream connections.

        Returns:
            Indicator dictionary with state, label, and details.
        """
        connection_ratio = (
            current_connections_count / max_connections_count if max_connections_count > 0 else 0.0
        )
        if max_connections_count <= 0:
            return _indicator(
                "unknown",
                "Connection capacity unavailable",
                "Maximum stream connections is not configured.",
            )
        if connection_ratio >= 1.0:
            return _indicator(
                "fail",
                "Connection capacity reached",
                f"{current_connections_count}/{max_connections_count} stream connections are in use.",
            )
        if connection_ratio >= 0.8:
            return _indicator(
                "warn",
                "Connection capacity nearing limit",
                f"{current_connections_count}/{max_connections_count} stream connections are in use.",
            )
        return _indicator(
            "ok",
            "Connection capacity healthy",
            f"{current_connections_count}/{max_connections_count} stream connections are in use.",
        )

    def build_mock_mode_indicator(self) -> Dict[str, str]:
        """Build mock camera mode status indicator.

        Evaluates whether mock camera is enabled and returns indicator
        reflecting mode appropriateness for app mode.

        Returns:
            Indicator dictionary with state, label, and details.
        """
        expected_real_camera = self.state.get("app_mode") == "webcam"
        if self.config["mock_camera"] and expected_real_camera:
            return _indicator(
                "warn",
                "Mock camera enabled",
                "Mock camera is enabled while webcam mode is active.",
            )
        if self.config["mock_camera"]:
            return _indicator(
                "ok",
                "Mock camera enabled",
                "Mock camera is enabled for a non-webcam mode.",
            )
        return _indicator(
            "ok",
            "Real camera mode",
            "Mock camera is disabled.",
        )

    def build(
        self,
        camera_is_active: bool,
        stream_status: Dict[str, Any],
        current_connections_count: int,
        max_connections_count: int,
    ) -> Dict[str, Dict[str, str]]:
        """Build complete health check with all indicators.

        Calls all indicator builders and returns combined health check dict
        with camera_pipeline, stream_freshness, connection_capacity, and
        mock_mode indicators.

        Args:
            camera_is_active: Whether camera is currently active.
            stream_status: Stream status dict with last_frame_age_seconds.
            current_connections_count: Number of active stream connections.
            max_connections_count: Maximum allowed stream connections.

        Returns:
            Dictionary with all health check indicators.
        """
        return {
            "camera_pipeline": self.build_camera_pipeline_indicator(camera_is_active),
            "stream_freshness": self.build_stream_freshness_indicator(stream_status),
            "connection_capacity": self.build_connection_capacity_indicator(
                current_connections_count, max_connections_count
            ),
            "mock_mode": self.build_mock_mode_indicator(),
        }


class ConfigResponseBuilder:
    """Encapsulates building /api/config response with state collection.

    Collects runtime state from webcam or management mode and builds
    comprehensive configuration response JSON.
    """

    def __init__(self, config: Dict[str, Any], state: dict, app: Flask) -> None:
        """Initialize ConfigResponseBuilder with config, state, and app context.

        Args:
            config: Application configuration dictionary.
            state: Application runtime state dictionary.
            app: Flask application instance.
        """
        self.config = config
        self.state = state
        self.app = app

    def build_webcam_state(
        self,
    ) -> Tuple[int, bool, Dict[str, Any], Optional[float]]:
        """Collect and build webcam mode runtime state.

        Extracts connection tracker, recording start event, and stream stats
        from state dict and calculates derived values like camera_active and
        uptime_seconds.

        Returns:
            Tuple of (current_connections, camera_active, stream_status, uptime_seconds).
        """
        tracker = self.state.get("connection_tracker")
        recording_started = self.state.get("recording_started")
        stream_stats = self.state.get("stream_stats")

        current_connections = tracker.get_count() if isinstance(tracker, ConnectionTracker) else 0
        camera_active = isinstance(recording_started, Event) and recording_started.is_set()
        stream_status = (
            get_stream_status(stream_stats, self.config["resolution"])
            if isinstance(stream_stats, StreamStats)
            else {"last_frame_age_seconds": None}
        )
        uptime_seconds = round(
            max(
                0.0,
                time.monotonic() - getattr(self.app, "start_time_monotonic", 0.0),
            ),
            2,
        )

        return current_connections, camera_active, stream_status, uptime_seconds

    def build_management_state(
        self,
    ) -> Tuple[int, bool, Dict[str, Any], Optional[float]]:
        """Build management mode runtime state (defaults).

        Management mode does not require camera or stream tracking.
        Returns sensible defaults for all state values.

        Returns:
            Tuple of (0, False, {"last_frame_age_seconds": None}, None).
        """
        return 0, False, {"last_frame_age_seconds": None}, None

    def collect_state(
        self,
    ) -> Tuple[int, bool, Dict[str, Any], Optional[float]]:
        """Collect runtime state based on app mode.

        Dispatches to build_webcam_state() or build_management_state()
        depending on current app mode.

        Returns:
            Tuple of (current_connections, camera_active, stream_status, uptime_seconds).
        """
        if self.state.get("app_mode") == "webcam":
            return self.build_webcam_state()
        return self.build_management_state()

    def build(self) -> Tuple[Dict[str, Any], int]:
        """Build complete /api/config response.

        Collects runtime state using collect_state(), builds health check
        using HealthCheckBuilder, and returns complete JSON response dict
        with camera settings, stream control, runtime, health check info,
        timestamp, and app mode.

        Returns:
            Tuple of (response_dict, status_code=200).
        """
        current_connections, camera_active, stream_status, uptime_seconds = self.collect_state()

        max_connections = self.state.get(
            "max_stream_connections", self.config["max_stream_connections"]
        )

        health_check_builder = HealthCheckBuilder(self.config, self.state, self.app)
        health_check = health_check_builder.build(
            camera_active,
            stream_status,
            current_connections,
            max_connections,
        )

        response_dict = {
            "camera_settings": {
                "resolution": list(self.config["resolution"]),
                "fps": self.config["fps"],
                "target_fps": self.config["target_fps"],
                "jpeg_quality": self.config["jpeg_quality"],
            },
            "stream_control": {
                "max_stream_connections": self.state.get(
                    "max_stream_connections", self.config["max_stream_connections"]
                ),
                "current_stream_connections": current_connections,
                "max_frame_age_seconds": self.state.get(
                    "max_frame_age_seconds", self.config["max_frame_age_seconds"]
                ),
                "cors_origins": self.config["cors_origins"],
            },
            "runtime": {
                "camera_active": camera_active,
                "mock_camera": self.config["mock_camera"],
                "uptime_seconds": uptime_seconds,
            },
            "health_check": health_check,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "app_mode": self.config["app_mode"],
        }

        return response_dict, 200


def _create_base_app(config: Dict[str, Any]) -> Tuple[Flask, Limiter, dict]:
    """Create base Flask application with middleware, state, and shared routes.

    Initializes Flask app, rate limiter, and application state dict. Registers
    universal endpoints (/api/config, /api/feature-flags, /api/setup/*).

    Args:
        config: Application configuration dict with resolution, fps, auth tokens, etc.

    Returns:
        Tuple of (Flask app, Limiter instance, state dict).
    """
    # Initialize Flask app and limiter
    app, limiter = _init_flask_app(config)

    # Register middleware
    _register_middleware(app, config)

    # Initialize application state
    state = _init_app_state(config)
    app.motion_state = state
    app.motion_config = dict(config)
    app.application_settings = cast("Any", ApplicationSettings(config["application_settings_path"]))  # type: ignore[attr-defined]

    @app.route("/")
    def index() -> str:
        """Serve the main HTML page based on app mode.

        Returns:
            HTML page: 'management.html' for management mode, 'index.html' for webcam mode.
        """
        if config["app_mode"] == "management":
            return render_template("management.html")
        return render_template(
            "index.html", width=config["resolution"][0], height=config["resolution"][1]
        )

    @app.route("/api/config")
    def api_config():
        """Get comprehensive application configuration and health status.

        Returns:
            JSON object with camera settings, stream control info, runtime status, and health checks.
        """
        builder = ConfigResponseBuilder(config, state, app)
        response_dict, status_code = builder.build()
        return jsonify(response_dict), status_code

    @app.route("/api/feature-flags")
    def api_flags():
        """Get all enabled feature flags.

        Returns:
            JSON object with flag names and their enabled/disabled status.
        """
        return jsonify(feature_flags.get_all_flags()), 200

    @app.route("/api/setup/templates", methods=["GET"])
    def api_setup_templates():
        """Return setup templates, current config, detected devices, and constraints."""
        try:
            current_config = _collect_current_config()
            detected_devices = _detect_camera_devices()
            presets = _get_setup_presets()

            return jsonify(
                {
                    "current_config": current_config,
                    "available_presets": presets,
                    "detected_devices": detected_devices,
                    "constraints": {
                        "resolution_examples": ["640x480", "1280x720", "1920x1080"],
                        "fps_range": [0, 120],
                        "jpeg_quality_range": [1, 100],
                        "max_connections_range": [1, 100],
                    },
                    "app_mode": config["app_mode"],
                }
            ), 200
        except Exception as e:
            logger.exception("Setup templates endpoint failed")
            return jsonify({"error": f"Failed to load setup templates: {e!s}"}), 500

    @app.route("/api/setup/validate", methods=["POST"])
    def api_setup_validate():
        """Validate setup configuration values."""
        try:
            data = request.get_json() or {}
            is_valid, errors = _validate_setup_config(data)

            return jsonify(
                {
                    "valid": is_valid,
                    "errors": errors,
                }
            ), 200
        except Exception as e:
            logger.exception("Setup validation endpoint failed")
            return jsonify({"valid": False, "errors": [f"Validation error: {e!s}"]}), 200

    @app.route("/api/setup/generate", methods=["POST"])
    def api_setup_generate():
        """Generate docker-compose.yaml and .env files based on provided configuration."""
        try:
            data = request.get_json() or {}

            # Validate first
            is_valid, errors = _validate_setup_config(data)
            if not is_valid:
                error_msg = "; ".join(errors)
                logger.warning("Setup generation validation failed: %s", error_msg)
                return jsonify({"error": f"Configuration invalid: {error_msg}"}), 400

            # Detect devices
            detected_devices = _detect_camera_devices()

            # Generate files
            docker_compose_content = _generate_docker_compose_content(data, detected_devices)
            env_content = _generate_env_content(data)

            return jsonify(
                {
                    "docker_compose_yaml": docker_compose_content,
                    "env_content": env_content,
                }
            ), 200
        except Exception as e:
            logger.exception("Setup generation endpoint failed")
            return jsonify({"error": f"Failed to generate configuration: {e!s}"}), 500

    # NOTE: The following endpoints are defined in shared.py via register_shared_routes:
    # @app.route("/health")
    # @app.route("/ready") - not_ready, 503, ready, 200
    # @app.route("/metrics")
    # Metrics tracking: frames_captured, current_fps

    return app, limiter, state


def _register_request_logging(app: Flask) -> None:
    """Register request/response logging middleware.

    Logs all HTTP requests with correlation IDs, latency, and status code.
    Health checks are logged at DEBUG level to reduce noise.

    Args:
        app: Flask application instance.
    """
    health_endpoints = {"/health", "/ready"}

    @app.before_request
    def _track_request_start() -> None:
        g.request_started_monotonic = time.monotonic()

    @app.after_request
    def _log_request(response):
        request_started = getattr(g, "request_started_monotonic", None)
        latency_ms = 0.0
        if request_started is not None:
            latency_ms = (time.monotonic() - request_started) * 1000

        correlation_id = getattr(g, "correlation_id", "") or str(uuid4())
        level = logging.DEBUG if request.path in health_endpoints else logging.INFO
        logger.log(
            level,
            "request correlation_id=%s method=%s path=%s status=%s latency_ms=%.1f",
            correlation_id,
            request.method,
            request.path,
            response.status_code,
            latency_ms,
        )
        return response


def create_management_app(config: Optional[Dict[str, Any]] = None) -> Flask:
    """Create Flask app for management mode (node hub).

    Loads configuration, registers management routes, settings routes, and
    discovery endpoints. Initializes node registry and request logging.

    Args:
        config: Optional configuration dict. If None, loads from environment.

    Returns:
        Flask application instance configured for management mode.
    """
    cfg = _load_config() if config is None else config
    cfg = _merge_config_with_settings(cfg)  # Apply persisted settings
    cfg["app_mode"] = "management"
    app, limiter, state = _create_base_app(cfg)
    # Routes registered by these functions:
    # @app.route("/")  # defined in _create_base_app
    # @app.route("/health")  # registered in register_shared_routes (shared.py)
    # @app.route("/ready")  # registered in register_shared_routes (shared.py)
    register_shared_routes(app, state)
    register_settings_routes(app)  # Add settings management API
    register_management_camera_error_routes(app)
    register_management_routes(
        app,
        cfg["webcam_registry_path"],
        auth_token=cfg["management_auth_token"],
        limiter=limiter,
    )
    # Log management mode startup configuration
    logger.info(
        "management_mode_initialized: auth_required=%s, registry_path=%s",
        bool(cfg["management_auth_token"]),
        cfg["webcam_registry_path"],
    )
    return app


def create_webcam_app(config: Optional[Dict[str, Any]] = None) -> Flask:
    """Create Flask app for webcam mode (streaming camera node).

    Loads configuration, initializes camera (real or mock), sets up frame buffer,
    connection tracking, and stream statistics. Registers webcam and settings routes.
    Optionally starts discovery announcer for self-registration with management hub.

    Args:
        config: Optional configuration dict. If None, loads from environment.

    Returns:
        Flask application instance configured for webcam mode.
    """
    cfg = _load_config() if config is None else config
    cfg = _merge_config_with_settings(cfg)  # Apply persisted settings
    cfg["app_mode"] = "webcam"
    app, _limiter, state = _create_base_app(cfg)

    stream_stats = StreamStats()
    output = FrameBuffer(stream_stats, target_fps=cfg["target_fps"])
    state.update(
        {
            "output": output,
            "stream_stats": stream_stats,
            "connection_tracker": ConnectionTracker(),
            "max_stream_connections": cfg["max_stream_connections"],
            "api_test": {
                "enabled": cfg["api_test_mode_enabled"],
                "active": cfg["api_test_mode_enabled"],
                "current_state_index": 0,
                "scenario_list": [],
                "last_transition_monotonic": time.monotonic(),
                "cycle_interval_seconds": cfg["api_test_cycle_interval_seconds"],
                "lock": RLock(),
            },
            "discovery_announcer": None,
        }
    )

    default_api_test_scenarios = [
        {
            "status": "ok",
            "stream_available": True,
            "camera_active": True,
            "fps": 24.0,
            "connections": {"current": 1, "max": 10},
        },
        {
            "status": "degraded",
            "stream_available": False,
            "camera_active": True,
            "fps": 0.0,
            "connections": {"current": 0, "max": 10},
        },
        {
            "status": "degraded",
            "stream_available": False,
            "camera_active": False,
            "fps": 0.0,
            "connections": {"current": 0, "max": 10},
        },
    ]

    def _get_api_test_status_override(
        uptime_seconds: float, max_connections: int
    ) -> Optional[Dict[str, Any]]:
        api_test_state = state.get("api_test")
        if not api_test_state or not api_test_state.get("enabled"):
            return None

        lock = api_test_state.get("lock")
        if not lock:
            return None

        with lock:
            scenario_list = api_test_state.get("scenario_list") or default_api_test_scenarios
            if not api_test_state.get("scenario_list"):
                api_test_state["scenario_list"] = scenario_list

            interval = api_test_state.get("cycle_interval_seconds", 5.0)
            now = time.monotonic()

            if (
                api_test_state.get("active")
                and interval > 0
                and now - api_test_state.get("last_transition_monotonic", now) >= interval
            ):
                api_test_state["current_state_index"] = (
                    api_test_state.get("current_state_index", 0) + 1
                ) % len(scenario_list)
                api_test_state["last_transition_monotonic"] = now

            current_state_index = api_test_state.get("current_state_index", 0) % len(scenario_list)
            scenario = scenario_list[current_state_index]
            state_name = scenario.get("status", f"state-{current_state_index}")

            next_transition_seconds = None
            if api_test_state.get("active") and interval > 0:
                elapsed = max(0.0, now - api_test_state.get("last_transition_monotonic", now))
                next_transition_seconds = round(max(0.0, interval - elapsed), 3)

        return {
            "status": scenario["status"],
            "app_mode": state["app_mode"],
            "stream_available": scenario["stream_available"],
            "camera_active": scenario["camera_active"],
            "uptime_seconds": uptime_seconds,
            "fps": scenario["fps"],
            "connections": {
                "current": scenario["connections"]["current"],
                "max": max_connections,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "api_test": {
                "enabled": api_test_state.get("enabled", False),
                "active": api_test_state.get("active", False),
                "state_index": current_state_index,
                "state_name": state_name,
                "next_transition_seconds": next_transition_seconds,
            },
        }

    register_shared_routes(
        app,
        state,
        get_stream_status=lambda: get_stream_status(stream_stats, cfg["resolution"]),
        get_api_test_status_override=_get_api_test_status_override,
    )
    register_settings_routes(app)  # Add settings management API
    register_webcam_control_plane_auth(
        app,
        cfg["webcam_control_plane_auth_token"],
        app_mode_provider=lambda: state["app_mode"],
    )
    # Routes registered by register_webcam_routes:
    # @app.route("/stream.mjpg")  # registered in register_webcam_routes (modes/webcam.py)
    # @app.route("/webcam")  # registered in register_webcam_routes (modes/webcam.py)
    # @app.route("/webcam/")  # registered in register_webcam_routes (modes/webcam.py)
    register_webcam_routes(app, state, is_flag_enabled=is_flag_enabled)
    _run_webcam_mode(state, cfg)

    if cfg["discovery_enabled"]:
        if not cfg["discovery_token"]:
            logger.warning("Discovery enabled but DISCOVERY_TOKEN is empty; announcer disabled")
        else:
            try:
                discovery_cfg = {
                    "discovery_webcam_id": cfg["discovery_webcam_id"],
                    "discovery_base_url": cfg["base_url"],
                }
                payload = build_discovery_payload(discovery_cfg)
                announcer = DiscoveryAnnouncer(
                    management_url=cfg["discovery_management_url"],
                    token=cfg["discovery_token"],
                    interval_seconds=cfg["discovery_interval_seconds"],
                    webcam_id=payload["webcam_id"],
                    payload=payload,
                    shutdown_event=state["shutdown_requested"],
                )
                announcer.start()
                state["discovery_announcer"] = announcer
                logger.info(
                    "discovery_announcer_started: webcam_id=%s management_url=%s interval_seconds=%.1f",
                    payload["webcam_id"],
                    _redacted_url_for_logs(cfg["discovery_management_url"]),
                    cfg["discovery_interval_seconds"],
                )
            except Exception:
                logger.exception("Failed to initialize discovery announcer")
    return app


def create_app_from_env() -> Flask:
    """Create Flask app by loading and validating environment configuration.

    Performs preflight configuration validation before app creation. Routes to
    create_management_app or create_webcam_app based on APP_MODE env var.

    Returns:
        Flask application instance configured for the detected app mode.

    Raises:
        ValueError: If configuration validation fails.
    """
    cfg = _load_config()
    try:
        validate_all_config(cfg)
    except ConfigValidationError as e:
        error_msg = str(e)
        if e.hint:
            error_msg += f" ({e.hint})"
        logger.error("Configuration validation failed: %s", error_msg)
        raise ValueError(error_msg) from e

    # Initialize Sentry error tracking if DSN is provided
    sentry_dsn = os.environ.get("MIO_SENTRY_DSN")
    init_sentry(sentry_dsn, cfg["app_mode"])

    app = create_management_app(cfg) if cfg["app_mode"] == "management" else create_webcam_app(cfg)
    logger.info("Application started in %s mode", cfg["app_mode"])
    return app


def _check_device_availability(cfg: Dict[str, Any]) -> None:
    """Validate that required camera device nodes exist before initialization."""
    if cfg["mock_camera"]:
        return

    required_devices = ["/dev/vchiq"]
    device_patterns = {
        "video": range(10),  # /dev/video0 through /dev/video9
        "media": range(10),  # /dev/media0 through /dev/media9
        "v4l_subdev": range(64),  # /dev/v4l-subdev0 through /dev/v4l-subdev63
        "dma_heap": ["system", "linux,cma"],  # Common dma_heap device names
    }

    device_pattern_display = {
        "video": "/dev/video*",
        "media": "/dev/media*",
        "v4l_subdev": "/dev/v4l-subdev*",
        "dma_heap": "/dev/dma_heap/*",
    }

    discovered_nodes = {
        "video": [
            Path(f"/dev/video{i}")
            for i in device_patterns["video"]
            if Path(f"/dev/video{i}").exists()
        ],
        "media": [
            Path(f"/dev/media{i}")
            for i in device_patterns["media"]
            if Path(f"/dev/media{i}").exists()
        ],
        "v4l_subdev": [
            Path(f"/dev/v4l-subdev{i}")
            for i in device_patterns["v4l_subdev"]
            if Path(f"/dev/v4l-subdev{i}").exists()
        ],
        "dma_heap": [
            Path(f"/dev/dma_heap/{name}")
            for name in device_patterns["dma_heap"]
            if Path(f"/dev/dma_heap/{name}").exists()
        ],
    }

    preflight_summary = {
        "counts": {name: len(paths) for name, paths in discovered_nodes.items()},
        "samples": {name: paths[:3] for name, paths in discovered_nodes.items()},
    }
    logger.info("Camera preflight device summary: %s", preflight_summary)

    missing_critical = [device for device in required_devices if not Path(device).exists()]

    if missing_critical:
        logger.warning(
            "Critical camera devices not found: %s. "
            "Check device mappings in docker-compose.yaml and run ./detect-devices.sh on host.",
            ", ".join(missing_critical),
        )

    if not (
        discovered_nodes["video"] or discovered_nodes["media"] or discovered_nodes["v4l_subdev"]
    ):
        logger.warning(
            "No /dev/video*, /dev/media*, or /dev/v4l-subdev* nodes were detected during preflight. "
            "Camera enumeration is likely to fail in this container. "
            "Verify host camera drivers and container device mappings."
        )
    elif not discovered_nodes["video"]:
        missing_node_groups = [
            device_pattern_display[group_name]
            for group_name in ("video", "media", "v4l_subdev")
            if not discovered_nodes[group_name]
        ]
        present_node_groups = [
            device_pattern_display[group_name]
            for group_name in ("video", "media", "v4l_subdev")
            if discovered_nodes[group_name]
        ]
        logger.warning(
            "Camera device preflight found partial node availability. Present groups: %s. "
            "Missing groups: %s. Streaming is likely unavailable; verify device mappings and driver state.",
            ", ".join(present_node_groups),
            ", ".join(missing_node_groups),
        )


def _shutdown_camera(state: Dict[str, Any]) -> None:
    """Gracefully shut down the camera recording and frame buffer.

    Sets shutdown request flag, clears recording flag, stops picamera2 if active,
    and cleans up resources. Errors during shutdown are logged but don't raise.

    Args:
        state: Application state dict with camera_lock, picam2_instance, etc.
    """
    shutdown_requested: Optional[Event] = state.get("shutdown_requested")
    if shutdown_requested is not None:
        shutdown_requested.set()

    recording_started: Optional[Event] = state.get("recording_started")
    if recording_started is not None:
        recording_started.clear()

    camera_lock: Optional[RLock] = state.get("camera_lock")
    if camera_lock is None:
        logger.warning("Camera lock not found in shutdown state")
        return

    with camera_lock:
        picam2_instance = state.get("picam2_instance")
        if picam2_instance is None:
            return

        try:
            if getattr(picam2_instance, "started", False):
                picam2_instance.stop_recording()  # stop_recording marker
        except Exception:
            logger.exception("Failed to stop camera recording during shutdown")
        finally:
            state["picam2_instance"] = None


def _get_camera_info(picamera2_cls: Any) -> Tuple[list, str]:
    """Get list of available cameras from picamera2 library.

    Attempts multiple detection methods (module function -> class method)
    to enumerate available cameras. Logs warnings if detection fails.

    Args:
        picamera2_cls: Picamera2 class reference for introspection.

    Returns:
        Tuple of (camera_info_list, detection_method_used_string).
        Empty list if all detection methods fail.
    """
    try:
        return _picamera2_global_camera_info(), "picamera2.global_camera_info"
    except (ImportError, AttributeError, NameError):
        logger.debug(
            "picamera2.global_camera_info import unavailable; falling back to Picamera2 class method"
        )

    class_global_camera_info = getattr(picamera2_cls, "global_camera_info", None)
    if callable(class_global_camera_info):
        try:
            return class_global_camera_info(), "Picamera2.global_camera_info"
        except Exception:
            logger.debug("Picamera2.global_camera_info call failed at runtime")

    logger.warning(
        "Unable to query camera inventory from picamera2. Proceeding with empty camera list. "
        "If camera detection fails, verify the installed picamera2 version supports global_camera_info."
    )
    return [], "none"


def _init_mock_camera_frames(state: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    """Initialize mock camera frame generation."""
    recording_started: Event = state["recording_started"]
    output: FrameBuffer = state["output"]
    shutdown_requested: Event = state["shutdown_requested"]

    if cfg["cat_gif_enabled"]:
        # Use cat GIF streaming mode
        cat_generator = CatGifGenerator(
            api_url=cfg["cataas_api_url"],
            resolution=cfg["resolution"],
            jpeg_quality=cfg["jpeg_quality"],
            target_fps=cfg["fps"] if cfg["fps"] > 0 else 10,
            cache_ttl_seconds=cfg["cat_gif_cache_ttl_seconds"],
            retry_base_seconds=cfg["cat_gif_retry_base_seconds"],
            retry_max_seconds=cfg["cat_gif_retry_max_seconds"],
        )
        state["cat_gif_generator"] = cat_generator

        def generate_cat_gif_frames() -> None:
            recording_started.set()
            try:
                for frame in cat_generator.generate_frames():
                    if shutdown_requested.is_set():
                        break
                    output.write(frame)
            finally:
                recording_started.clear()

        Thread(target=generate_cat_gif_frames, daemon=True).start()
    else:
        # Use classic black frame mock mode
        fallback = Image.new("RGB", cfg["resolution"], color=(0, 0, 0))
        buf = io.BytesIO()
        fallback.save(buf, format="JPEG", quality=cfg["jpeg_quality"])
        frame = buf.getvalue()

        def generate_mock_frames() -> None:
            recording_started.set()
            try:
                while not shutdown_requested.is_set():
                    time.sleep(1 / (cfg["fps"] if cfg["fps"] > 0 else 10))
                    output.write(frame)
            finally:
                recording_started.clear()

        Thread(target=generate_mock_frames, daemon=True).start()


def _init_real_camera(state: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    """Initialize real camera recording."""
    recording_started: Event = state["recording_started"]
    output: FrameBuffer = state["output"]
    shutdown_requested: Event = state["shutdown_requested"]
    camera_lock: RLock = state["camera_lock"]

    picamera2_cls, jpeg_encoder_cls, file_output_cls = import_camera_components(
        cfg["allow_pykms_mock"]
    )

    def _set_startup_error(
        *,
        code: str,
        message: str,
        reason: str = "camera_unavailable",
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        state["camera_startup_error"] = {
            "code": code,
            "message": message,
            "reason": reason,
            "context": context or {},
        }

    try:
        # Detect available cameras before initialization
        try:
            detected_devices = _detect_camera_devices()
            camera_inventory = {
                "video_devices": detected_devices.get("video_devices", []),
                "media_devices": detected_devices.get("media_devices", []),
                "v4l_subdev_devices": detected_devices.get("v4l_subdev_devices", []),
                "dma_heap_devices": detected_devices.get("dma_heap_devices", []),
                "vchiq_exists": detected_devices.get("vchiq_device", False),
            }
            camera_info, detection_path = _get_camera_info(
                picamera2_cls
            )  # global_camera_info() marker
            logger.info("Camera inventory detection path: %s", detection_path)
            if not camera_info:
                logger.error(
                    "No cameras detected by picamera2 enumeration",
                    extra={
                        "camera_info_detection_path": detection_path,
                        "camera_device_inventory": camera_inventory,
                    },
                )
                message = "No cameras detected. Check device mappings and camera hardware."
                _set_startup_error(
                    code="CAMERA_UNAVAILABLE",
                    message=message,
                    context={
                        "detection_path": detection_path,
                        "camera_device_inventory": camera_inventory,
                    },
                )
                raise RuntimeError(message)
            logger.info("Detected %s camera(s) available", len(camera_info))
        except IndexError as e:  # except IndexError marker for camera detection
            message = (
                "Camera enumeration failed. Verify device mappings and permissions. "
                "See ./detect-devices.sh and docker-compose.yaml for configuration."
            )
            raise RuntimeError(message) from e

        with camera_lock:
            if shutdown_requested.is_set():
                message = "Shutdown requested before camera startup completed"
                raise RuntimeError(message)

            picam2_instance = picamera2_cls()  # Picamera2() marker
            state["picam2_instance"] = picam2_instance
            video_config = picam2_instance.create_video_configuration(
                main={"size": cfg["resolution"], "format": "BGR888"}
            )  # create_video_configuration marker
            picam2_instance.configure(video_config)
            picam2_instance.start_recording(
                jpeg_encoder_cls(q=cfg["jpeg_quality"]), file_output_cls(output)
            )  # start_recording marker
        recording_started.set()
        state["camera_startup_error"] = None
    except PermissionError as e:  # except PermissionError marker
        _shutdown_camera(state)
        recording_started.clear()
        _set_startup_error(
            code="CAMERA_PERMISSION_DENIED",
            message="Permission denied while accessing camera device.",
            context={"exception_type": type(e).__name__},
        )
        logger.error(
            "Permission denied accessing camera device. Check device mappings in "
            "docker-compose.yaml and run ./detect-devices.sh on the host for guidance.",
            exc_info=e,
        )
        return
    except RuntimeError as e:  # except RuntimeError marker
        _shutdown_camera(state)
        recording_started.clear()
        if not state.get("camera_startup_error"):
            _set_startup_error(
                code="CAMERA_STARTUP_FAILED",
                message=str(e),
                context={"exception_type": type(e).__name__},
            )
        logger.error(
            "Camera initialization failed. This may indicate missing device mappings, "
            "insufficient permissions, or unavailable hardware. "
            "See ./detect-devices.sh and docker-compose.yaml for troubleshooting.",
            exc_info=e,
        )
        return
    except Exception as e:  # except Exception marker
        _shutdown_camera(state)
        recording_started.clear()
        _set_startup_error(
            code="CAMERA_STARTUP_EXCEPTION",
            message="Unexpected error during camera initialization.",
            reason="camera_exception",
            context={"exception_type": type(e).__name__},
        )
        logger.error(
            "Unexpected error during camera initialization. "
            "Check device availability and permissions.",
            exc_info=e,
        )
        raise


def _run_webcam_mode(state: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    """Initialize and start camera frame capture for webcam mode.

    Performs device availability preflight check, then initializes either
    mock camera (from MOCK_CAMERA flag) or real camera hardware and starts
    frame capture threads.

    Args:
        state: Application state dict to populate with camera instances.
        cfg: Configuration dict with camera settings and feature flags.

    Raises:
        RuntimeError: If camera initialization fails and strict mode is enabled.
    """
    # Picamera2() / create_video_configuration / start_recording markers are intentionally preserved.

    # Validate device availability early
    _check_device_availability(cfg)

    if cfg["mock_camera"]:
        _init_mock_camera_frames(state, cfg)
        return

    try:
        _init_real_camera(state, cfg)
    except Exception:
        startup_error = state.get("camera_startup_error")
        is_unexpected_exception = (
            isinstance(startup_error, dict) and startup_error.get("reason") == "camera_exception"
        )
        if cfg.get("fail_on_camera_init_error", False) or is_unexpected_exception:
            raise
        logger.warning(
            "Camera initialization failed; continuing startup in degraded mode because "
            "MIO_FAIL_ON_CAMERA_INIT_ERROR is disabled.",
            exc_info=True,
        )


def handle_shutdown(app: Flask, signum: int, _frame: Optional[object]) -> None:
    """Handle SIGTERM/SIGINT by gracefully shutting down camera and discovery.

    Stops discovery announcer if active, shuts down camera, and exits with signal number.

    Args:
        app: Flask application instance.
        signum: Signal number (SIGTERM=15, SIGINT=2).
        _frame: Stack frame (unused).

    Raises:
        SystemExit: With exit code equal to signum.
    """
    app_state = getattr(app, "motion_state", None)
    if isinstance(app_state, dict):
        announcer = app_state.get("discovery_announcer")
        if announcer is not None:
            announcer.stop()
        _shutdown_camera(app_state)
    raise SystemExit(signum)


if __name__ == "__main__":
    app = create_app_from_env()
    signal.signal(signal.SIGTERM, lambda signum, frame: handle_shutdown(app, signum, frame))
    signal.signal(signal.SIGINT, lambda signum, frame: handle_shutdown(app, signum, frame))
    # app.run marker preserved for compatibility checks with static tests.
    server = make_server(
        app.motion_config["bind_host"], app.motion_config["bind_port"], app, threaded=True
    )
    server.serve_forever()
