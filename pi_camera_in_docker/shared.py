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
    app: Flask,
    state: dict,
    get_stream_status: Optional[Callable[[], dict]] = None,
    get_api_test_status_override: Optional[Callable[[float, int], Optional[dict]]] = None,
) -> None:
    api_test_scenarios = [
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

    def _get_api_test_payload(uptime_seconds: float, max_connections: int) -> Optional[dict]:
        api_test_state = state.get("api_test")
        if not api_test_state or not api_test_state.get("enabled"):
            return None

        lock = api_test_state.get("lock")
        if not lock:
            return None
        
        with lock:
            scenario_list = api_test_state.get("scenario_list") or api_test_scenarios
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
                elapsed = max(
                    0.0, now - api_test_state.get("last_transition_monotonic", now)
                )
                next_transition_seconds = round(max(0.0, interval - elapsed), 3)

        connections = {
            "current": scenario["connections"]["current"],
            "max": max_connections,
        }
        return {
            "status": scenario["status"],
            "app_mode": state["app_mode"],
            "stream_available": scenario["stream_available"],
            "camera_active": scenario["camera_active"],
            "uptime_seconds": uptime_seconds,
            "fps": scenario["fps"],
            "connections": connections,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "api_test": {
                "enabled": api_test_state.get("enabled", False),
                "active": api_test_state.get("active", False),
                "state_index": current_state_index,
                "state_name": state_name,
                "next_transition_seconds": next_transition_seconds,
            },
        }

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
        uptime_seconds = round(
            time.monotonic() - getattr(app, "start_time_monotonic", time.monotonic()), 2
        )
        max_connections = state.get("max_stream_connections", 0)

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

        overall_status = "ok" if stream_available else "degraded"
        return {
            "status": overall_status,
            "app_mode": state["app_mode"],
            "stream_available": stream_available,
            "camera_active": is_recording,
            "uptime_seconds": uptime_seconds,
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

        uptime_seconds = round(
            time.monotonic() - getattr(app, "start_time_monotonic", time.monotonic()), 2
        )
        max_connections = state.get("max_stream_connections", 0)

        api_test_payload = None
        if get_api_test_status_override is not None:
            api_test_payload = get_api_test_status_override(uptime_seconds, max_connections)
        else:
            api_test_payload = _get_api_test_payload(uptime_seconds, max_connections)

        if api_test_payload is not None:
            return jsonify(api_test_payload), 200

        return jsonify(_build_webcam_status_payload()), 200
