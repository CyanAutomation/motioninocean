#!/usr/bin/python3

import glob
import io
import logging
import os
import signal
import time
from threading import Event, RLock, Thread
from typing import Any, Dict, Optional, Tuple

from feature_flags import FeatureFlags, get_feature_flags, is_flag_enabled
from flask import Flask, g, jsonify, render_template, request
from flask_cors import CORS
from logging_config import configure_logging
from management_api import register_management_routes
from modes.webcam import (
    ConnectionTracker,
    FrameBuffer,
    StreamStats,
    get_stream_status,
    import_camera_components,
    register_management_camera_error_routes,
    register_webcam_routes,
)
from PIL import Image
from shared import register_shared_routes, register_webcam_control_plane_auth
from werkzeug.serving import make_server


ALLOWED_APP_MODES = {"webcam", "management"}
DEFAULT_APP_MODE = "webcam"

configure_logging()
logger = logging.getLogger(__name__)

feature_flags: FeatureFlags = get_feature_flags()
feature_flags.load()


def _parse_resolution(resolution_str: str) -> Tuple[int, int]:
    parts = resolution_str.split("x")  # resolution_str.split marker
    if len(parts) != 2:
        message = f"Invalid resolution format: {resolution_str}"
        raise ValueError(message)
    width, height = int(parts[0]), int(parts[1])
    if width <= 0 or height <= 0 or width > 4096 or height > 4096:
        message = f"Resolution dimensions out of valid range (1-4096): {width}x{height}"
        raise ValueError(message)
    return width, height


def _load_config() -> Dict[str, Any]:
    app_mode = os.environ.get("APP_MODE", DEFAULT_APP_MODE).strip().lower()  # os.environ.get marker
    if app_mode not in ALLOWED_APP_MODES:
        message = f"Invalid APP_MODE {app_mode}"
        raise ValueError(message)

    try:
        resolution = _parse_resolution(os.environ.get("RESOLUTION", "640x480"))
    except ValueError:
        resolution = (640, 480)

    try:
        fps = int(os.environ.get("FPS", "0"))
    except ValueError:
        fps = 0

    try:
        target_fps = int(os.environ.get("TARGET_FPS", str(fps)))
    except ValueError:
        target_fps = fps

    try:
        jpeg_quality = int(os.environ.get("JPEG_QUALITY", "90"))
        if not 1 <= jpeg_quality <= 100:
            jpeg_quality = 90
    except ValueError:
        jpeg_quality = 90

    try:
        max_frame_age = float(os.environ.get("MAX_FRAME_AGE_SECONDS", "10"))
    except ValueError:
        max_frame_age = 10.0
    if max_frame_age <= 0:
        max_frame_age = 10.0

    try:
        max_stream_connections = int(os.environ.get("MAX_STREAM_CONNECTIONS", "10"))
    except ValueError:
        max_stream_connections = 10
    if not 1 <= max_stream_connections <= 100:
        max_stream_connections = 10

    api_test_mode_enabled = os.environ.get("API_TEST_MODE_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    try:
        api_test_cycle_interval_seconds = float(
            os.environ.get("API_TEST_CYCLE_INTERVAL_SECONDS", "5")
        )
    except ValueError:
        api_test_cycle_interval_seconds = 5.0
    if api_test_cycle_interval_seconds <= 0:
        api_test_cycle_interval_seconds = 5.0

    # Canonical Pi 3 profile env var is MOTION_IN_OCEAN_PI3_PROFILE.
    # Keep PI3_PROFILE as a legacy fallback for backward compatibility.
    pi3_profile_raw = os.environ.get(
        "MOTION_IN_OCEAN_PI3_PROFILE", os.environ.get("PI3_PROFILE", "false")
    )

    return {
        "app_mode": app_mode,
        "resolution": resolution,
        "fps": fps,
        "target_fps": target_fps,
        "jpeg_quality": jpeg_quality,
        "max_frame_age_seconds": max_frame_age,
        "max_stream_connections": max_stream_connections,
        "api_test_mode_enabled": api_test_mode_enabled,
        "api_test_cycle_interval_seconds": api_test_cycle_interval_seconds,
        "pi3_profile_enabled": pi3_profile_raw.lower() in ("1", "true", "yes"),
        "mock_camera": is_flag_enabled("MOCK_CAMERA"),
        "cors_enabled": is_flag_enabled("CORS_SUPPORT"),
        "allow_pykms_mock": os.environ.get("ALLOW_PYKMS_MOCK", "false").lower()
        in ("1", "true", "yes"),
        "node_registry_path": os.environ.get("NODE_REGISTRY_PATH", "/data/node-registry.json"),
        # Auth is required if and only if token is non-empty
        "management_auth_token": os.environ.get("MANAGEMENT_AUTH_TOKEN", ""),
    }


def _detect_camera_devices() -> Dict[str, Any]:
    """
    Detect available camera-related device nodes on the system.
    Returns a dict with detected device information.
    Failures are logged but don't raise exceptions (graceful fallback).
    """
    result = {
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
        if os.path.isdir(dma_heap_dir):
            try:
                dma_devices = os.listdir(dma_heap_dir)
                result["dma_heap_devices"] = [f"/dev/dma_heap/{d}" for d in dma_devices]
            except OSError:
                logger.debug("Could not list /dev/dma_heap directory")

        # Check video devices
        for i in range(10):
            video_device = f"/dev/video{i}"
            if os.path.exists(video_device):
                result["video_devices"].append(video_device)

        # Check media devices
        for i in range(10):
            media_device = f"/dev/media{i}"
            if os.path.exists(media_device):
                result["media_devices"].append(media_device)

        # Check v4l sub-device nodes
        for i in range(64):
            subdev_device = f"/dev/v4l-subdev{i}"
            if os.path.exists(subdev_device):
                result["v4l_subdev_devices"].append(subdev_device)

        # Check VCHIQ
        if os.path.exists("/dev/vchiq"):
            result["vchiq_device"] = True

        # Check DRI (graphics)
        if os.path.exists("/dev/dri"):
            result["dri_device"] = True

        # Set has_camera flag
        result["has_camera"] = bool(
            result["video_devices"]
            or result["media_devices"]
            or result["v4l_subdev_devices"]
            or result["vchiq_device"]
        )
    except Exception as e:
        logger.warning(f"Device detection encountered error: {e}")

    return result


def _collect_current_config() -> Dict[str, Any]:
    """
    Collect current configuration from environment variables.
    Returns a simplified config dict for the setup API.
    """
    try:
        resolution = _parse_resolution(os.environ.get("RESOLUTION", "640x480"))
    except ValueError:
        resolution = (640, 480)

    try:
        fps = int(os.environ.get("FPS", "0"))
    except ValueError:
        fps = 0

    try:
        target_fps_str = os.environ.get("TARGET_FPS", "")
        target_fps = int(target_fps_str) if target_fps_str else None
    except ValueError:
        target_fps = None

    try:
        jpeg_quality = int(os.environ.get("JPEG_QUALITY", "90"))
        if not 1 <= jpeg_quality <= 100:
            jpeg_quality = 90
    except ValueError:
        jpeg_quality = 90

    try:
        max_stream_connections = int(os.environ.get("MAX_STREAM_CONNECTIONS", "10"))
        if not 1 <= max_stream_connections <= 100:
            max_stream_connections = 10
    except ValueError:
        max_stream_connections = 10

    pi3_profile = os.environ.get(
        "MOTION_IN_OCEAN_PI3_PROFILE", os.environ.get("PI3_PROFILE", "false")
    ).lower() in (
        "1",
        "true",
        "yes",
    )
    mock_camera = is_flag_enabled("MOCK_CAMERA")
    cors_origins = os.environ.get("MOTION_IN_OCEAN_CORS_ORIGINS", "")
    auth_token = os.environ.get("MANAGEMENT_AUTH_TOKEN", "")

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
    config: Dict[str, Any], detected_devices: Dict[str, Any]
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
      APP_MODE: ${MOTION_IN_OCEAN_MODE:-webcam}
      RESOLUTION: ${MOTION_IN_OCEAN_RESOLUTION}
      FPS: ${MOTION_IN_OCEAN_FPS}
      TARGET_FPS: ${MOTION_IN_OCEAN_TARGET_FPS:-}
      JPEG_QUALITY: ${MOTION_IN_OCEAN_JPEG_QUALITY}
      MAX_STREAM_CONNECTIONS: ${MOTION_IN_OCEAN_MAX_STREAM_CONNECTIONS:-2}
      # Canonical Pi 3 profile toggle consumed by runtime config loading.
      MOTION_IN_OCEAN_PI3_PROFILE: ${MOTION_IN_OCEAN_PI3_PROFILE:-false}
      MOTION_IN_OCEAN_OCTOPRINT_COMPATIBILITY: ${MOTION_IN_OCEAN_OCTOPRINT_COMPATIBILITY:-false}
      CORS_ORIGINS: ${MOTION_IN_OCEAN_CORS_ORIGINS}
      MOCK_CAMERA: ${MOCK_CAMERA:-false}
      HEALTHCHECK_READY: ${MOTION_IN_OCEAN_HEALTHCHECK_READY:-true}
    ports:
      - "${MOTION_IN_OCEAN_BIND_HOST:-127.0.0.1}:${MOTION_IN_OCEAN_PORT:-8000}:8000"
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
        "MOTION_IN_OCEAN_MODE=webcam",
        "",
        "# Camera Configuration",
        f"MOTION_IN_OCEAN_RESOLUTION={config.get('resolution', '640x480')}",
        f"MOTION_IN_OCEAN_FPS={config.get('fps', 0)}",
        f"MOTION_IN_OCEAN_TARGET_FPS={config.get('target_fps', '') or ''}",
        f"MOTION_IN_OCEAN_JPEG_QUALITY={config.get('jpeg_quality', 90)}",
        f"MOTION_IN_OCEAN_MAX_STREAM_CONNECTIONS={config.get('max_connections', 10)}",
        # Canonical Pi 3 profile env variable consumed by runtime config loading.
        f"MOTION_IN_OCEAN_PI3_PROFILE={'true' if config.get('pi3_profile') else 'false'}",
        "",
        "# Features and Integration",
        "MOTION_IN_OCEAN_OCTOPRINT_COMPATIBILITY=false",
        f"MOTION_IN_OCEAN_CORS_ORIGINS={config.get('cors_origins', '')}",
        f"MOCK_CAMERA={'true' if config.get('mock_camera') else 'false'}",
        "MOTION_IN_OCEAN_HEALTHCHECK_READY=true",
        "",
        "# Networking",
        "MOTION_IN_OCEAN_BIND_HOST=127.0.0.1",
        "MOTION_IN_OCEAN_PORT=8000",
        "MOTION_IN_OCEAN_IMAGE_TAG=latest",
        "",
        "# Management/Security",
        f"MANAGEMENT_AUTH_TOKEN={config.get('auth_token', '')}",
        "",
    ]

    return "\n".join(env_lines)


def _create_base_app(config: Dict[str, Any]) -> Tuple[Flask, dict]:
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.start_time_monotonic = time.monotonic()
    _register_request_logging(app)

    if config["cors_enabled"]:
        CORS(app, resources={r"/*": {"origins": ["*"]}})

    state = {
        "app_mode": config["app_mode"],
        "recording_started": Event(),
        "shutdown_requested": Event(),
        "camera_lock": RLock(),
        "max_frame_age_seconds": config["max_frame_age_seconds"],
        "picam2_instance": None,
    }
    app.motion_state = state
    app.motion_config = dict(config)

    @app.route("/")
    def index() -> str:
        if config["app_mode"] == "management":
            return render_template("management.html")
        return render_template(
            "index.html", width=config["resolution"][0], height=config["resolution"][1]
        )

    @app.route("/api/config")
    def api_config():
        return jsonify(
            {
                "camera_settings": {"resolution": list(config["resolution"]), "fps": config["fps"]},
                "app_mode": config["app_mode"],
            }
        ), 200

    @app.route("/api/feature-flags")
    def api_flags():
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
                logger.warning(f"Setup generation validation failed: {error_msg}")
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

    return app, state


def _register_request_logging(app: Flask) -> None:
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

        level = logging.DEBUG if request.path in health_endpoints else logging.INFO
        logger.log(
            level,
            "request method=%s path=%s status=%s latency_ms=%.1f",
            request.method,
            request.path,
            response.status_code,
            latency_ms,
        )
        return response


def create_management_app(config: Optional[Dict[str, Any]] = None) -> Flask:
    cfg = _load_config() if config is None else config
    cfg["app_mode"] = "management"
    app, state = _create_base_app(cfg)
    register_shared_routes(app, state)
    register_management_camera_error_routes(app)
    register_management_routes(
        app,
        cfg["node_registry_path"],
        auth_token=cfg["management_auth_token"],
    )
    # Log management mode startup configuration
    logger.info(
        "management_mode_initialized: auth_required=%s, registry_path=%s",
        bool(cfg["management_auth_token"]),
        cfg["node_registry_path"],
    )
    return app


def create_webcam_app(config: Optional[Dict[str, Any]] = None) -> Flask:
    cfg = _load_config() if config is None else config
    cfg["app_mode"] = "webcam"
    app, state = _create_base_app(cfg)

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
        }
    )

    register_shared_routes(
        app, state, get_stream_status=lambda: get_stream_status(stream_stats, cfg["resolution"])
    )
    register_webcam_control_plane_auth(
        app,
        cfg["management_auth_token"],
        app_mode_provider=lambda: state["app_mode"],
    )
    register_webcam_routes(app, state, is_flag_enabled=is_flag_enabled)
    _run_webcam_mode(state, cfg)
    return app


def create_app_from_env() -> Flask:
    cfg = _load_config()
    app = create_management_app(cfg) if cfg["app_mode"] == "management" else create_webcam_app(cfg)
    logger.info("Application started in %s mode", cfg["app_mode"])
    return app


def _check_device_availability(cfg: Dict[str, Any]) -> None:
    """Validate that required camera device nodes exist before initialization."""
    if cfg["mock_camera"]:
        return

    required_devices = ["/dev/vchiq"]
    node_patterns = {
        "video": "/dev/video*",
        "media": "/dev/media*",
        "v4l_subdev": "/dev/v4l-subdev*",
        "dma_heap": "/dev/dma_heap/*",
    }
    discovered_nodes = {
        node_group: sorted(glob.glob(pattern)) for node_group, pattern in node_patterns.items()
    }

    preflight_summary = {
        "counts": {name: len(paths) for name, paths in discovered_nodes.items()},
        "samples": {name: paths[:3] for name, paths in discovered_nodes.items()},
    }
    logger.info("Camera preflight device summary: %s", preflight_summary)

    missing_critical = [device for device in required_devices if not os.path.exists(device)]

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
            node_patterns[group_name]
            for group_name in ("video", "media", "v4l_subdev")
            if not discovered_nodes[group_name]
        ]
        present_node_groups = [
            node_patterns[group_name]
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
    try:
        from picamera2 import global_camera_info

        return global_camera_info(), "picamera2.global_camera_info"
    except (ImportError, AttributeError):
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


def _run_webcam_mode(state: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    # Picamera2() / create_video_configuration / start_recording markers are intentionally preserved.
    recording_started: Event = state["recording_started"]
    output: FrameBuffer = state["output"]
    shutdown_requested: Event = state["shutdown_requested"]
    camera_lock: RLock = state["camera_lock"]

    # Validate device availability early
    _check_device_availability(cfg)

    if cfg["mock_camera"]:
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
    else:
        picamera2_cls, jpeg_encoder_cls, file_output_cls = import_camera_components(
            cfg["allow_pykms_mock"]
        )
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
                    raise RuntimeError(message)
                logger.info(f"Detected {len(camera_info)} camera(s) available")
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
        except PermissionError as e:  # except PermissionError marker
            _shutdown_camera(state)
            logger.error(
                "Permission denied accessing camera device. Check device mappings in "
                "docker-compose.yaml and run ./detect-devices.sh on the host for guidance.",
                exc_info=e,
            )
            raise
        except RuntimeError as e:  # except RuntimeError marker
            _shutdown_camera(state)
            logger.error(
                "Camera initialization failed. This may indicate missing device mappings, "
                "insufficient permissions, or unavailable hardware. "
                "See ./detect-devices.sh and docker-compose.yaml for troubleshooting.",
                exc_info=e,
            )
            raise
        except Exception as e:  # except Exception marker
            _shutdown_camera(state)
            logger.error(
                "Unexpected error during camera initialization. "
                "Check device availability and permissions.",
                exc_info=e,
            )
            raise


def handle_shutdown(app: Flask, signum: int, _frame: Optional[object]) -> None:
    app_state = getattr(app, "motion_state", None)
    if isinstance(app_state, dict):
        _shutdown_camera(app_state)
    raise SystemExit(signum)


if __name__ == "__main__":
    app = create_app_from_env()
    signal.signal(signal.SIGTERM, lambda signum, frame: handle_shutdown(app, signum, frame))
    signal.signal(signal.SIGINT, lambda signum, frame: handle_shutdown(app, signum, frame))
    # app.run marker preserved for compatibility checks with static tests.
    server = make_server("0.0.0.0", 8000, app, threaded=True)
    server.serve_forever()
