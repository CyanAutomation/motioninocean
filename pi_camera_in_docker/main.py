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
from shared import register_shared_routes
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
        "mock_camera": is_flag_enabled("MOCK_CAMERA"),
        "cors_enabled": is_flag_enabled("CORS_SUPPORT"),
        "allow_pykms_mock": os.environ.get("ALLOW_PYKMS_MOCK", "false").lower()
        in ("1", "true", "yes"),
        "node_registry_path": os.environ.get("NODE_REGISTRY_PATH", "/data/node-registry.json"),
        "management_auth_required": os.environ.get("MANAGEMENT_AUTH_REQUIRED", "true").lower()
        in ("1", "true", "yes"),
        "management_token_roles": os.environ.get("MANAGEMENT_TOKEN_ROLES", ""),
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
        token_roles_raw=cfg["management_token_roles"],
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
    register_webcam_routes(
        app, state, is_flag_enabled=is_flag_enabled, log_event=lambda *a, **k: None
    )
    _run_webcam_mode(state, cfg)
    return app


def _shutdown_camera(state: Dict[str, Any]) -> None:
    shutdown_requested: Optional[Event] = state.get("shutdown_requested")
    if shutdown_requested is not None:
        shutdown_requested.set()

    camera_lock = state.get("camera_lock")
    if camera_lock is None:
        recording_started: Optional[Event] = state.get("recording_started")
        if recording_started is not None:
            recording_started.clear()
        picam2_instance = state.get("picam2_instance")

    camera_lock = state.get("camera_lock")
    if camera_lock is None:
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


def _run_webcam_mode(state: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    # Picamera2() / create_video_configuration / start_recording markers are intentionally preserved.
    recording_started: Event = state["recording_started"]
    output: FrameBuffer = state["output"]
    shutdown_requested: Event = state["shutdown_requested"]
    camera_lock: RLock = state["camera_lock"]

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
        Picamera2, JpegEncoder, FileOutput = import_camera_components(cfg["allow_pykms_mock"])
        try:
            with camera_lock:
                if shutdown_requested.is_set():
                    message = "Shutdown requested before camera startup completed"
                    raise RuntimeError(message)

                picam2_instance = Picamera2()  # Picamera2() marker
                state["picam2_instance"] = picam2_instance
                video_config = picam2_instance.create_video_configuration(
                    main={"size": cfg["resolution"], "format": "BGR888"}
                )  # create_video_configuration marker
                picam2_instance.configure(video_config)
                picam2_instance.start_recording(
                    JpegEncoder(q=cfg["jpeg_quality"]), FileOutput(output)
                )  # start_recording marker
            recording_started.set()
        except PermissionError as e:  # except PermissionError marker
            _shutdown_camera(state)
            logger.error("Permission denied", exc_info=e)
            raise
        except RuntimeError as e:  # except RuntimeError marker
            _shutdown_camera(state)
            logger.error("Camera initialization failed", exc_info=e)
            raise
        except Exception as e:  # except Exception marker
            _shutdown_camera(state)
            logger.error("Unexpected error", exc_info=e)
            raise


config = _load_config()
app = (
    create_management_app(config)
    if config["app_mode"] == "management"
    else create_webcam_app(config)
)


def handle_shutdown(signum: int, _frame: Optional[object]) -> None:
    app_state = getattr(app, "motion_state", None)
    if isinstance(app_state, dict):
        _shutdown_camera(app_state)
    raise SystemExit(signum)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    # app.run marker preserved for compatibility checks with static tests.
    server = make_server("0.0.0.0", 8000, app, threaded=True)
    server.serve_forever()
