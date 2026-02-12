import time
from datetime import datetime, timezone
from typing import Callable, Optional

from flask import Flask, jsonify, request


def extract_bearer_token(auth_header: str) -> Optional[str]:
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:].strip()
    return token or None


def register_webcam_control_plane_auth(
    app: Flask, auth_token: str, app_mode_provider: Callable[[], str]
) -> None:
    protected_exact_paths = {"/health", "/ready", "/metrics", "/api/status"}

    @app.before_request
    def _webcam_control_plane_auth_guard():
        if app_mode_provider() != "webcam":
            return None
        if not auth_token:
            return None

        path = request.path
        if path not in protected_exact_paths and not path.startswith("/api/actions/"):
            return None

        token = extract_bearer_token(request.headers.get("Authorization", ""))
        if token is None or token != auth_token:
            return (
                jsonify(
                    {
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "authentication required",
                            "details": {},
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    }
                ),
                401,
            )
        return None


def register_shared_routes(
    app: Flask, state: dict, get_stream_status: Optional[Callable[[], dict]] = None
) -> None:
    def _build_management_status_payload() -> dict:
        return {
            "status": "ok",
            "app_mode": state.get("app_mode", "unknown"),
            "stream_available": False,
            "camera_active": False,
            "uptime_seconds": round(time.monotonic() - getattr(app, 'start_time_monotonic', time.monotonic()), 2),
            "fps": 0.0,
            "connections": {"current": 0, "max": 0},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _build_webcam_status_payload() -> dict:
        stream_status = (
            get_stream_status()
            if get_stream_status
            else {
                "current_fps": 0.0,
                "last_frame_age_seconds": None,
            }
        )
        is_recording = state.get("recording_started") and state["recording_started"].is_set()
        last_frame_age_seconds = stream_status.get("last_frame_age_seconds")
        max_age = state.get("max_frame_age_seconds", 10.0)
        is_frame_fresh = (
            last_frame_age_seconds is not None and last_frame_age_seconds <= max_age
        )
        stream_available = is_recording and is_frame_fresh

        tracker = state.get("connection_tracker")
        current_connections = tracker.get_count() if tracker else 0
        max_connections = state.get("max_stream_connections", 0)

        overall_status = "ok" if stream_available else "degraded"
        return {
            "status": overall_status,
            "app_mode": state["app_mode"],
            "stream_available": stream_available,
            "camera_active": is_recording,
            "uptime_seconds": round(time.monotonic() - getattr(app, 'start_time_monotonic', time.monotonic()), 2),
            "fps": stream_status.get("current_fps", 0.0),
            "connections": {
                "current": current_connections,
                "max": max_connections,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

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
                    "reason": "no_camera_required",
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

    @app.route("/api/status")
    def api_status():
        if state["app_mode"] != "webcam":
            return jsonify(_build_management_status_payload()), 200
        return jsonify(_build_webcam_status_payload()), 200
