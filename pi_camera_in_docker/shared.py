import time
from datetime import datetime
from typing import Callable, Optional

from flask import Flask, jsonify


def register_shared_routes(
    app: Flask, state: dict, get_stream_status: Optional[Callable[[], dict]] = None
) -> None:
    @app.route("/health")
    def health():
        return jsonify(
            {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "app_mode": state["app_mode"],
            }
        ), 200

    @app.route("/ready")
    def ready():
        if state["app_mode"] != "webcam":
            return jsonify(
                {
                    "status": "ready",
                    "reason": "camera_disabled_for_management_mode",
                    "app_mode": state["app_mode"],
                    "timestamp": datetime.now().isoformat(),
                }
            ), 200

        status = get_stream_status() if get_stream_status else {"last_frame_age_seconds": None}
        is_recording = state["recording_started"].is_set()
        last_frame_age_seconds = status.get("last_frame_age_seconds")
        max_age = state["max_frame_age_seconds"]
        stale = last_frame_age_seconds is not None and last_frame_age_seconds > max_age
        if is_recording and last_frame_age_seconds is not None and not stale:
            return jsonify({"status": "ready", "app_mode": state["app_mode"], **status}), 200
        return jsonify({"status": "not_ready", "app_mode": state["app_mode"], **status}), 503

    @app.route("/metrics")
    def metrics():
        status = (
            get_stream_status()
            if get_stream_status
            else {
                "frames_captured": 0,
                "current_fps": 0.0,
                "last_frame_age_seconds": None,
            }
        )
        return jsonify(
            {
                "app_mode": state["app_mode"],
                "camera_mode_enabled": state["app_mode"] == "webcam",
                "camera_active": state["recording_started"].is_set(),
                "max_frame_age_seconds": state["max_frame_age_seconds"],
                "uptime_seconds": round(time.monotonic() - app.start_time_monotonic, 2),
                **status,
                "timestamp": datetime.now().isoformat(),
            }
        ), 200
