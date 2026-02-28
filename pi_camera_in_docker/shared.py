import json as _json
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from flask import Flask, Response, jsonify, request

from pi_camera_in_docker.version_info import get_app_version_info


def extract_bearer_token(auth_header: str) -> Optional[str]:
    """Extract bearer token from Authorization header.

    Parses standard HTTP Authorization header (format: "Bearer <token>").
    Case-insensitive scheme matching per RFC 7235.

    Args:
        auth_header: Raw Authorization header value.

    Returns:
        Bearer token string, or None if header is missing/malformed or token empty.
    """
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:].strip()
    return token or None


def register_webcam_control_plane_auth(
    app: Flask, auth_token: str, app_mode_provider: Callable[[], str]
) -> None:
    """Register Flask before_request guard for webcam control plane authentication.

    Protects webcam mode endpoints with bearer token validation. Routes protected:
    - /health, /ready, /metrics, /api/status, /version, /api/version (exact match)
    - /api/actions/* (prefix match)

    Management mode requests bypass protection (app_mode == 'management').
    If auth_token is empty, protection is disabled (no-op).

    Args:
        app: Flask application instance.
        auth_token: Bearer token required for access. Empty string disables protection.
        app_mode_provider: Callable returning current app mode ('webcam' or 'management').

    Raises:
        Generates HTTP 401 Unauthorized response if token is missing/invalid.
    """
    protected_exact_paths = {"/health", "/ready", "/metrics", "/api/status", "/version", "/api/version"}

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


def _get_api_test_payload(
    state: dict, api_test_scenarios: list, uptime_seconds: float, max_connections: int
) -> Optional[dict]:
    """Get API test scenario override payload if enabled.

    Args:
        state: Shared app state dict with api_test configuration.
        api_test_scenarios: List of scenario dicts to cycle through.
        uptime_seconds: Application uptime in seconds.
        max_connections: Maximum concurrent connections allowed.

    Returns:
        API test payload dict if enabled, else None.
    """
    api_test_state = state.get("api_test")
    if not api_test_state or not api_test_state.get("enabled"):
        return None

    lock = api_test_state.get("lock")
    if not lock:
        return None

    with lock:
        scenario_list = api_test_state.get("scenario_list")
        if not isinstance(scenario_list, list) or not scenario_list:
            scenario_list = api_test_scenarios
            api_test_state["scenario_list"] = scenario_list

        if not scenario_list:
            return None

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
        if not isinstance(scenario, dict):
            scenario = api_test_scenarios[0] if api_test_scenarios else None
            if scenario is None:
                return None
        state_name = scenario.get("status", f"state-{current_state_index}")

        next_transition_seconds = None
        if api_test_state.get("active") and interval > 0:
            elapsed = max(0.0, now - api_test_state.get("last_transition_monotonic", now))
            next_transition_seconds = round(max(0.0, interval - elapsed), 3)

    safe_scenario = _safe_api_test_scenario(scenario)
    if safe_scenario is None:
        return None

    connections = {
        "current": safe_scenario["connections"]["current"],
        "max": max_connections,
    }
    return {
        "status": safe_scenario["status"],
        "app_mode": state["app_mode"],
        "stream_available": safe_scenario["stream_available"],
        "camera_active": safe_scenario["camera_active"],
        "uptime_seconds": uptime_seconds,
        "fps": safe_scenario["fps"],
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


def _safe_api_test_scenario(scenario: Any) -> Optional[dict[str, Any]]:
    """Validate required scenario keys and return a safe normalized shape.

    Args:
        scenario: Candidate scenario object.

    Returns:
        Normalized scenario dict containing required keys, or None if invalid.
    """
    if not isinstance(scenario, dict):
        return None

    connections = scenario.get("connections")
    if not isinstance(connections, dict):
        return None

    required_fields = ["status", "stream_available", "camera_active", "fps"]
    if any(field not in scenario for field in required_fields):
        return None
    if "current" not in connections:
        return None

    return {
        "status": scenario["status"],
        "stream_available": scenario["stream_available"],
        "camera_active": scenario["camera_active"],
        "fps": scenario["fps"],
        "connections": {"current": connections["current"]},
    }


def _build_management_status_payload(app: Flask, state: dict) -> dict:
    """Build status payload for management mode.

    Args:
        app: Flask application instance.
        state: Shared app state dict.

    Returns:
        Status payload dict.
    """
    return {
        "status": "ok",
        "app_mode": state.get("app_mode", "unknown"),
        "stream_available": False,
        "camera_active": False,
        "uptime_seconds": round(
            time.monotonic() - getattr(app, "start_time_monotonic", time.monotonic()), 2
        ),
        "fps": 0.0,
        "connections": {"current": 0, "max": 0},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _build_webcam_status_payload(
    app: Flask,
    state: dict,
    get_stream_status: Optional[Callable[[], dict]] = None,
) -> dict:
    """Build status payload for webcam mode.

    Args:
        app: Flask application instance.
        state: Shared app state dict.
        get_stream_status: Optional callback returning stream statistics.

    Returns:
        Status payload dict.
    """
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
    is_frame_fresh = last_frame_age_seconds is not None and last_frame_age_seconds <= max_age
    stream_available = is_recording and is_frame_fresh

    tracker = state.get("connection_tracker")
    current_connections = tracker.get_count() if tracker else 0

    overall_status = "ok" if stream_available else "degraded"
    payload = {
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
    startup_error = state.get("camera_startup_error")
    if startup_error:
        payload["camera_error"] = startup_error
    return payload


def _build_not_ready_reason(state: dict) -> dict[str, Any]:
    """Build optional reason payload for webcam not-ready responses."""
    startup_error = state.get("camera_startup_error")
    if not startup_error:
        return {"reason": "initializing"}

    reason = startup_error.get("reason") if isinstance(startup_error, dict) else None
    return {
        "reason": reason or "camera_unavailable",
        "camera_error": startup_error,
    }


def _build_metrics_payload(
    app: Flask, state: dict, stream_status: dict[str, Any]
) -> dict[str, Any]:
    """Build metrics payload that matches the MetricsSnapshot contract.

    Args:
        app: Flask application instance.
        state: Shared app state dict.
        stream_status: Stream metrics callback payload.

    Returns:
        Metrics payload aligned with docs/openapi.yaml MetricsSnapshot schema.
    """
    metrics_stream_fields = {
        "frames_captured",
        "current_fps",
        "last_frame_age_seconds",
    }
    filtered_stream_status = {
        key: value for key, value in stream_status.items() if key in metrics_stream_fields
    }
    return {
        "app_mode": state["app_mode"],
        "camera_mode_enabled": state["app_mode"] == "webcam",
        "camera_active": state.get("recording_started", threading.Event()).is_set(),
        "max_frame_age_seconds": state.get("max_frame_age_seconds", 10.0),
        "uptime_seconds": round(time.monotonic() - getattr(app, "start_time_monotonic", time.monotonic()), 2),
        **filtered_stream_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def register_shared_routes(
    app: Flask,
    state: dict,
    get_stream_status: Optional[Callable[[], dict]] = None,
    get_api_test_status_override: Optional[Callable[[float, int], Optional[dict]]] = None,
) -> None:
    """Register universal health check and status endpoints.

    Registers four routes on the Flask app:
    - GET /health: App is running (lightweight, always 200)
    - GET /ready: App is ready to serve (503 if webcam not initialized)
    - GET /metrics: Prometheus-style metrics snapshot
    - GET /api/status: Detailed status including stream/camera/connection state
    - GET /version and /api/version: Application version metadata

    Behavior varies by app_mode:
    - 'webcam': /ready waits for first frame; /api/status includes stream stats
    - 'management': /ready returns immediately; /api/status is stub

    Provides API test mode support for deterministic testing via state['api_test'].

    Args:
        app: Flask application instance.
        state: Shared app state dict with keys:
            - 'app_mode': 'webcam' or 'management'
            - 'max_stream_connections': Max concurrent stream limit
            - 'max_frame_age_seconds': Staleness threshold for ready probe
            - 'recording_started': threading.Event for camera initialization
            - 'connection_tracker': Optional ConnectionTracker instance (webcam mode)
            - 'api_test': Optional dict for API test scenario cycling
        get_stream_status: Optional callback returning dict with 'current_fps',
            'last_frame_age_seconds', 'frames_captured'.
        get_api_test_status_override: Optional callback for custom test payload override.
    """
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

    @app.route("/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "timestamp": datetime.now(timezone.utc).isoformat(),
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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ), 200

        status = get_stream_status() if get_stream_status else {"last_frame_age_seconds": None}
        is_recording = state["recording_started"].is_set()
        last_frame_age_seconds = status.get("last_frame_age_seconds")
        max_age = state["max_frame_age_seconds"]
        stale = last_frame_age_seconds is not None and last_frame_age_seconds > max_age
        if is_recording and last_frame_age_seconds is not None and not stale:
            return jsonify({"status": "ready", "app_mode": state["app_mode"], **status}), 200
        reason_payload = _build_not_ready_reason(state)
        return jsonify(
            {"status": "not_ready", "app_mode": state["app_mode"], **reason_payload, **status}
        ), 503

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
        return jsonify(_build_metrics_payload(app, state, status)), 200

    @app.route("/api/metrics/stream")
    def metrics_stream() -> Response:
        """Stream metrics as Server-Sent Events.

        Pushes the same payload as GET /metrics every 3 seconds over a persistent
        HTTP connection. Replaces the browser's polling setInterval loop with a
        single long-lived connection, eliminating ~30 HTTP requests/minute.
        The browser EventSource API reconnects automatically on disconnect.

        Returns:
            Streaming text/event-stream response with JSON metrics data frames.
        """

        def _generate():  # type: ignore[return]
            try:
                while True:
                    stream_status = (
                        get_stream_status()
                        if get_stream_status
                        else {
                            "frames_captured": 0,
                            "current_fps": 0.0,
                            "last_frame_age_seconds": None,
                        }
                    )
                    payload = _build_metrics_payload(app, state, stream_status)
                    yield f"data: {_json.dumps(payload)}\n\n"
                    time.sleep(3)
            except GeneratorExit:
                pass

        sse_response = Response(_generate(), mimetype="text/event-stream")
        sse_response.headers["Cache-Control"] = "no-cache"
        sse_response.headers["X-Accel-Buffering"] = "no"
        sse_response.headers["Connection"] = "keep-alive"
        return sse_response

    @app.route("/version")
    @app.route("/api/version")
    def version():
        version_info = get_app_version_info()
        return jsonify(
            {
                "status": "ok",
                "version": version_info["version"],
                "source": version_info["source"],
                "app_mode": state["app_mode"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ), 200

    @app.route("/api/status")
    def api_status():
        if state["app_mode"] != "webcam":
            return jsonify(_build_management_status_payload(app, state)), 200

        uptime_seconds = round(
            time.monotonic() - getattr(app, "start_time_monotonic", time.monotonic()), 2
        )
        max_connections = state.get("max_stream_connections", 0)

        api_test_payload = None
        if get_api_test_status_override is not None:
            api_test_payload = get_api_test_status_override(uptime_seconds, max_connections)
        else:
            api_test_payload = _get_api_test_payload(
                state, api_test_scenarios, uptime_seconds, max_connections
            )

        if api_test_payload is not None:
            return jsonify(api_test_payload), 200

        return jsonify(_build_webcam_status_payload(app, state, get_stream_status)), 200
