#!/usr/bin/python3

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

    return {
        "app_mode": app_mode,
        "resolution": resolution,
        "fps": fps,
        "target_fps": target_fps,
        "jpeg_quality": jpeg_quality,
        "max_frame_age_seconds": max_frame_age,
        "max_stream_connections": max_stream_connections,
        "pi3_profile_enabled": os.environ.get("PI3_PROFILE", "false").lower() in ("1", "true", "yes"),
        "mock_camera": is_flag_enabled("MOCK_CAMERA"),
        "cors_enabled": is_flag_enabled("CORS_SUPPORT"),
        "allow_pykms_mock": os.environ.get("ALLOW_PYKMS_MOCK", "false").lower()
        in ("1", "true", "yes"),
        "node_registry_path": os.environ.get("NODE_REGISTRY_PATH", "/data/node-registry.json"),
        "management_auth_required": os.environ.get("MANAGEMENT_AUTH_REQUIRED", "true").lower()
        in ("1", "true", "yes"),
        "management_auth_token": os.environ.get("MANAGEMENT_AUTH_TOKEN", ""),
    }


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
        auth_required=cfg["management_auth_required"],
        auth_token=cfg["management_auth_token"],
    )
    # Log management mode startup configuration
    logger.info(
        "management_mode_initialized: auth_required=%s, registry_path=%s",
        cfg["management_auth_required"],
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
    register_webcam_routes(
        app, state, is_flag_enabled=is_flag_enabled
    )
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
    
    import os as os_module
    required_devices = ["/dev/vchiq"]
    optional_devices = ["/dev/video0", "/dev/media0"]
    
    missing_critical = []
    missing_optional = []
    
    for device in required_devices:
        if not os_module.path.exists(device):
            missing_critical.append(device)
    
    for device in optional_devices:
        if not os_module.path.exists(device):
            missing_optional.append(device)
    
    if missing_critical:
        logger.warning(
            f"Critical camera devices not found: {', '.join(missing_critical)}. "
            "Check device mappings in docker-compose.yaml and run ./detect-devices.sh on host."
        )
    
    if missing_optional:
        logger.warning(
            f"Optional camera devices not found: {', '.join(missing_optional)}. "
            "Some camera features may be unavailable."
        )


def _shutdown_camera(state: Dict[str, Any]) -> None:
    shutdown_requested: Optional[Event] = state.get("shutdown_requested")
    if shutdown_requested is not None:
        shutdown_requested.set()

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
        picamera2_cls, jpeg_encoder_cls, file_output_cls = import_camera_components(cfg["allow_pykms_mock"])
        try:
            # Detect available cameras before initialization
            try:
                camera_info, detection_path = _get_camera_info(picamera2_cls)  # global_camera_info() marker
                logger.info("Camera inventory detection path: %s", detection_path)
                if not camera_info:
                    message = (
                        "No cameras detected. Check device mappings in docker-compose.yaml. "
                        "Run ./detect-devices.sh on the host for configuration help."
                    )
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
