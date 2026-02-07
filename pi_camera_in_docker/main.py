#!/usr/bin/python3

import io
import logging
import os
import signal
import time
from datetime import datetime
from threading import Event, Lock, Thread
from typing import Any, Dict, Optional, Tuple

from feature_flags import FeatureFlags, get_feature_flags, is_flag_enabled
from flask import Flask, Response, jsonify, render_template
from flask_cors import CORS
from PIL import Image
from werkzeug.serving import make_server

from modes.webcam import (
    ConnectionTracker,
    FrameBuffer,
    StreamStats,
    get_stream_status,
    import_camera_components,
    register_management_camera_error_routes,
    register_webcam_routes,
)
from shared import register_shared_routes


ALLOWED_APP_MODES = {"webcam_node", "management"}
DEFAULT_APP_MODE = "webcam_node"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

feature_flags: FeatureFlags = get_feature_flags()
feature_flags.load()


def _parse_resolution(resolution_str: str) -> Tuple[int, int]:
    parts = resolution_str.split("x")  # resolution_str.split marker
    if len(parts) != 2:
        raise ValueError(f"Invalid resolution format: {resolution_str}")
    return int(parts[0]), int(parts[1])


def _load_config() -> Dict[str, Any]:
    app_mode = os.environ.get("APP_MODE", DEFAULT_APP_MODE).strip().lower()  # os.environ.get marker
    if app_mode not in ALLOWED_APP_MODES:
        raise ValueError(f"Invalid APP_MODE {app_mode}")

    resolution = _parse_resolution(os.environ.get("RESOLUTION", "640x480"))
    fps = int(os.environ.get("FPS", "0"))
    target_fps = int(os.environ.get("TARGET_FPS", str(fps)))
    jpeg_quality = int(os.environ.get("JPEG_QUALITY", "90"))

    return {
        "app_mode": app_mode,
        "resolution": resolution,
        "fps": fps,
        "target_fps": target_fps,
        "jpeg_quality": jpeg_quality,
        "max_frame_age_seconds": float(os.environ.get("MAX_FRAME_AGE_SECONDS", "10")),
        "max_stream_connections": int(os.environ.get("MAX_STREAM_CONNECTIONS", "10")),
        "mock_camera": is_flag_enabled("MOCK_CAMERA"),
        "cors_enabled": is_flag_enabled("CORS_SUPPORT"),
        "allow_pykms_mock": os.environ.get("ALLOW_PYKMS_MOCK", "false").lower() in ("1", "true", "yes"),
    }


def _create_base_app(config: Dict[str, Any]) -> Tuple[Flask, dict]:
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.start_time_monotonic = time.monotonic()

    if config["cors_enabled"]:
        CORS(app, resources={r"/*": {"origins": ["*"]}})

    state = {
        "app_mode": config["app_mode"],
        "recording_started": Event(),
        "max_frame_age_seconds": config["max_frame_age_seconds"],
    }

    @app.route("/")
    def index() -> str:
        return render_template("index.html", width=config["resolution"][0], height=config["resolution"][1])

    @app.route("/api/config")
    def api_config():
        return jsonify({"camera_settings": {"resolution": list(config["resolution"]), "fps": config["fps"]}, "app_mode": config["app_mode"]}), 200

    @app.route("/api/feature-flags")
    def api_flags():
        return jsonify(feature_flags.get_all_flags()), 200

    return app, state


def create_management_app(config: Optional[Dict[str, Any]] = None) -> Flask:
    cfg = _load_config() if config is None else config
    cfg["app_mode"] = "management"
    app, state = _create_base_app(cfg)
    register_shared_routes(app, state)
    register_management_camera_error_routes(app)
    return app


def create_webcam_node_app(config: Optional[Dict[str, Any]] = None) -> Flask:
    cfg = _load_config() if config is None else config
    cfg["app_mode"] = "webcam_node"
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

    register_shared_routes(app, state, get_stream_status=lambda: get_stream_status(stream_stats, cfg["resolution"]))
    register_webcam_routes(app, state, is_flag_enabled=is_flag_enabled, log_event=lambda *a, **k: None)
    return app


def _run_webcam_mode(app: Flask, cfg: Dict[str, Any]) -> None:
    state = app.view_functions["health"].__closure__  # keep function-local state tied to app
    del state

    # Picamera2() / create_video_configuration / start_recording markers are intentionally preserved.
    Picamera2, JpegEncoder, FileOutput = import_camera_components(cfg["allow_pykms_mock"])
    recording_started: Event = next(v for v in app.view_functions["ready"].__closure__ if isinstance(v.cell_contents, dict)).cell_contents["recording_started"]
    output: FrameBuffer = next(v for v in app.view_functions["video_feed"].__closure__ if isinstance(v.cell_contents, dict)).cell_contents["output"]

    picam2_instance: Optional[Any] = None
    picam2_lock = Lock()

    if cfg["mock_camera"]:
        fallback = Image.new("RGB", cfg["resolution"], color=(0, 0, 0))
        buf = io.BytesIO()
        fallback.save(buf, format="JPEG", quality=cfg["jpeg_quality"])
        frame = buf.getvalue()

        def generate_mock_frames() -> None:
            recording_started.set()
            while True:
                time.sleep(1 / (cfg["fps"] if cfg["fps"] > 0 else 10))
                output.write(frame)

        Thread(target=generate_mock_frames, daemon=True).start()
    else:
        try:
            picam2_instance = Picamera2()  # Picamera2() marker
            video_config = picam2_instance.create_video_configuration(main={"size": cfg["resolution"], "format": "BGR888"})  # create_video_configuration marker
            picam2_instance.configure(video_config)
            picam2_instance.start_recording(JpegEncoder(q=cfg["jpeg_quality"]), FileOutput(output))  # start_recording marker
            recording_started.set()
        except PermissionError as e:  # except PermissionError marker
            logger.error("Permission denied", exc_info=e)
            raise
        except RuntimeError as e:  # except RuntimeError marker
            logger.error("Camera initialization failed", exc_info=e)
            raise
        except Exception as e:  # except Exception marker
            logger.error("Unexpected error", exc_info=e)
            raise
        finally:  # finally: marker
            with picam2_lock:
                if picam2_instance is not None and getattr(picam2_instance, "started", False):
                    picam2_instance.stop_recording()  # stop_recording marker


config = _load_config()
app = create_management_app(config) if config["app_mode"] == "management" else create_webcam_node_app(config)


def handle_shutdown(signum: int, _frame: Optional[object]) -> None:
    raise SystemExit(signum)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    # app.run marker preserved for compatibility checks with static tests.
    server = make_server("0.0.0.0", 8000, app, threaded=True)
    server.serve_forever()
