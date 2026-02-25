import io
import logging
import time
from collections import deque
from threading import Condition, Lock
from typing import Any, Dict, Optional, Tuple

import sentry_sdk
from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import BadRequest


"""Webcam mode implementation: camera frame capture, buffering, and MJPEG streaming.

Provides frame capture from Picamera2 hardware into a thread-safe buffer with
FPS statistics, connection tracking, and MJPEG stream endpoints.
"""

logger = logging.getLogger(__name__)


class StreamStats:
    """Thread-safe frame capture statistics.

    Tracks cumulative frame count, last frame timestamp, and calculates
    real-time FPS from a sliding window of frame timestamps.
    """

    def __init__(self) -> None:
        """Initialize statistics tracker."""
        self._lock = Lock()
        self._frame_count = 0
        self._last_frame_monotonic: Optional[float] = None
        self._frame_times_monotonic: deque[float] = deque(maxlen=30)

    def record_frame(self, monotonic_timestamp: float) -> None:
        """Record a captured frame.

        Args:
            monotonic_timestamp: Frame timestamp from time.monotonic().
        """
        with self._lock:
            self._frame_count += 1
            self._last_frame_monotonic = monotonic_timestamp
            self._frame_times_monotonic.append(monotonic_timestamp)

    def snapshot(self) -> Tuple[int, Optional[float], float]:
        """Atomically snapshot frame metrics for consistent reporting.

        Returns a tuple of (frame_count, last_frame_monotonic_time, current_fps).
        FPS is calculated from the most recent frame time window (up to 30 frames).
        If insufficient frame history exists, returns 0.0 fps.
        """
        with self._lock:
            frame_count = self._frame_count
            last_frame_time = self._last_frame_monotonic
            frame_times = list(self._frame_times_monotonic)

        # Need at least 2 frames to calculate meaningful FPS
        if len(frame_times) < 2:
            return frame_count, last_frame_time, 0.0

        # Calculate FPS from time span of recorded frames
        time_span = frame_times[-1] - frame_times[0]
        fps = 0.0 if time_span == 0 else (len(frame_times) - 1) / time_span
        return frame_count, last_frame_time, fps


class FrameBuffer(io.BufferedIOBase):
    """Thread-safe circular buffer for camera frame storage.

    Implements the output interface for Picamera2 JPEG encoder. Stores latest
    frame in memory and notifies waiting consumers via condition variable.
    Supports frame rate throttling to limit storage of rapidly arriving frames.
    """

    def __init__(
        self, stats: StreamStats, max_frame_size: Optional[int] = None, target_fps: int = 0
    ) -> None:
        """Initialize frame buffer.

        Args:
            stats: StreamStats instance for recording frame metrics.
            max_frame_size: Maximum allowed frame size in bytes (oversized frames skipped).
            target_fps: Target frames per second (0 = no throttling).
        """
        self.frame: Optional[bytes] = None
        self.condition = Condition()
        self._stats = stats
        self._max_frame_size = max_frame_size
        self._target_frame_interval = None if target_fps <= 0 else 1.0 / target_fps
        self._last_frame_monotonic: Optional[float] = None

    def write(self, buf: bytes) -> int:  # type: ignore
        """Write frame data from encoder (Picamera2 interface).

        Stores frame, records statistics, and notifies waiting consumers.
        Frame rate is throttled if target_fps > 0. Oversized frames are skipped.

        Args:
            buf: JPEG-encoded frame bytes from Picamera2 encoder.

        Returns:
            Number of bytes written (always len(buf), even if frame was skipped).
        """
        size = len(buf)
        if self._max_frame_size is not None and size > self._max_frame_size:
            return size
        with self.condition:
            now = time.monotonic()
            if (
                self._target_frame_interval is not None
                and self._last_frame_monotonic is not None
                and now < self._last_frame_monotonic + self._target_frame_interval
            ):
                return size
            self.frame = buf
            self._last_frame_monotonic = now
            self._stats.record_frame(now)
            self.condition.notify_all()
        return size


class ConnectionTracker:
    """Thread-safe counter for active stream connections.

    Tracks number of currently connected clients and enforces
    connection limits when streaming to multiple clients.
    """

    def __init__(self) -> None:
        """Initialize connection tracker."""
        self._count = 0
        self._lock = Lock()

    def increment(self) -> int:
        """Increment connection count.

        Returns:
            New total connection count.
        """
        with self._lock:
            self._count += 1
            return self._count

    def try_increment(self, max_connections: int) -> bool:
        """Attempt to increment within limit.

        Args:
            max_connections: Maximum allowed connections.

        Returns:
            True if successfully incremented, False if at limit.
        """
        with self._lock:
            if self._count >= max_connections:
                return False
            self._count += 1
            return True

    def decrement(self) -> int:
        """Decrement connection count.

        Returns:
            New total connection count.
        """
        with self._lock:
            self._count -= 1
            return self._count

    def get_count(self) -> int:
        """Get current connection count.

        Returns:
            Current number of connected clients.
        """
        with self._lock:
            return self._count


def import_camera_components(pykms_mock_fallback_enabled: bool):
    """Import Picamera2 and related encoder classes.

    Handles missing pykms dependencies by creating mock modules if allowed.
    This is necessary for development environments without full GPU support.

    Args:
        pykms_mock_fallback_enabled: If True, inject mock pykms modules for dev/test fallback.

    Returns:
        Tuple of (Picamera2 class, JpegEncoder class, FileOutput class).

    Raises:
        ModuleNotFoundError: If imports fail and mock is not allowed.
    """
    try:
        from picamera2 import Picamera2
    except (ModuleNotFoundError, AttributeError) as e:
        with sentry_sdk.new_scope() as scope:
            scope.set_tag("component", "camera")
            scope.capture_exception(e)
        if pykms_mock_fallback_enabled and (
            "pykms" in str(e) or "kms" in str(e) or "PixelFormat" in str(e)
        ):
            logger.warning("Activating internal dev/test pykms fallback during Picamera2 import")
            import sys
            import types

            pykms_mock = types.ModuleType("pykms")
            kms_mock = types.ModuleType("kms")

            class PixelFormatMock:
                RGB888 = "RGB888"
                XRGB8888 = "XRGB8888"
                BGR888 = "BGR888"
                XBGR8888 = "XBGR8888"

            pykms_mock.PixelFormat = PixelFormatMock  # type: ignore
            kms_mock.PixelFormat = PixelFormatMock  # type: ignore # type: ignore[attr-defined]
            sys.modules["pykms"] = pykms_mock
            sys.modules["kms"] = kms_mock
            from picamera2 import Picamera2
        else:
            raise

    from picamera2.encoders import JpegEncoder
    from picamera2.outputs import FileOutput

    return Picamera2, JpegEncoder, FileOutput


def get_stream_status(stats: StreamStats, resolution: Tuple[int, int]) -> Dict[str, Any]:
    """Get current stream statistics snapshot.

    Args:
        stats: StreamStats instance to query.
        resolution: Current camera resolution (width, height) tuple.

    Returns:
        Dict with frames_captured, current_fps, resolution, last_frame_age_seconds.
    """
    now = time.monotonic()
    frame_count, last_frame_time, current_fps = stats.snapshot()
    age = None if last_frame_time is None else round(now - last_frame_time, 2)
    return {
        "frames_captured": frame_count,
        "current_fps": round(current_fps, 2),
        "resolution": resolution,
        "last_frame_age_seconds": age,
    }


# Module-level constants for webcam routes
_SUPPORTED_ACTIONS = [
    "restart",
    "api-test-start",
    "api-test-stop",
    "api-test-reset",
    "api-test-step",
]

_DEFAULT_API_TEST_SCENARIOS = [
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


def _build_json_error(code: str, message: str, status_code: int) -> tuple[Response, int]:
    """Build a JSON error response with supported actions context.

    Args:
        code: Error code (e.g., 'ACTION_INVALID_BODY').
        message: Human-readable error message.
        status_code: HTTP status code.

    Returns:
        Tuple of (Response, int) with JSON error and status code.
    """
    return (
        jsonify(
            {
                "error": {
                    "code": code,
                    "message": message,
                    "details": {"supported_actions": _SUPPORTED_ACTIONS},
                }
            }
        ),
        status_code,
    )  # type: ignore[return-value]


def _parse_action_body() -> tuple[Optional[dict], Optional[tuple[Response, int]]]:
    """Parse and validate JSON action body from request.

    Checks that body is a valid JSON object with no unsupported keys.
    Allowed keys: interval_seconds, scenario_order.

    Returns:
        Tuple of (body_dict, error_response).
        If error, body_dict is None.
        If no error, error_response is None.
    """
    if not request.data:
        return None, None

    try:
        body = request.get_json(silent=False)
    except BadRequest:
        return None, _build_json_error(
            "ACTION_INVALID_BODY", "request body must be valid JSON", 400
        )

    if not isinstance(body, dict):
        return None, _build_json_error(
            "ACTION_INVALID_BODY", "request body must be a JSON object", 400
        )

    allowed_keys = {"interval_seconds", "scenario_order"}
    unknown_keys = sorted(set(body.keys()) - allowed_keys)
    if unknown_keys:
        return None, _build_json_error(
            "ACTION_INVALID_BODY",
            f"request body contains unsupported keys: {', '.join(unknown_keys)}",
            400,
        )

    return body, None


def _build_api_test_scenario_list(
    existing_scenarios: list[dict], scenario_order: Optional[list[int]]
) -> tuple[Optional[list[dict]], Optional[tuple[Response, int]]]:
    """Build scenario list with optional reordering.

    If scenario_order is provided, validates it and returns reordered scenarios.
    Validates that scenario_order is a list of unique integers with each scenario
    exactly once.

    Args:
        existing_scenarios: Current list of scenario dicts.
        scenario_order: Optional list of scenario indexes to reorder.

    Returns:
        Tuple of (scenario_list, error_response).
        If error, scenario_list is None.
        If no error, error_response is None.
    """
    if scenario_order is None:
        return existing_scenarios, None

    if not isinstance(scenario_order, list) or not scenario_order:
        return None, _build_json_error(
            "ACTION_INVALID_BODY", "scenario_order must be a non-empty array", 400
        )

    if not all(isinstance(index, int) for index in scenario_order):
        return None, _build_json_error(
            "ACTION_INVALID_BODY", "scenario_order must contain only integer indexes", 400
        )

    unique_indexes = set(scenario_order)
    max_index = len(existing_scenarios) - 1
    if unique_indexes != set(range(len(existing_scenarios))):
        return None, _build_json_error(
            "ACTION_INVALID_BODY",
            f"scenario_order must contain each scenario index exactly once from 0 to {max_index}",
            400,
        )

    return [existing_scenarios[index] for index in scenario_order], None


def _get_api_test_runtime_info(api_test_state: dict, scenario_list: list[dict]) -> dict:
    """Build API test runtime information dict.

    Extracts current state, scenario index, and calculates seconds until
    next transition based on cycle interval and elapsed time.

    Args:
        api_test_state: API test state dict with active, cycle_interval_seconds, etc.
        scenario_list: List of scenario dicts for cycling.

    Returns:
        Dict with enabled, active, state_index, state_name, next_transition_seconds.

    Raises:
        ValueError: If scenario_list is empty.
    """
    if not scenario_list:
        error_message = "scenario_list cannot be empty"
        raise ValueError(error_message)

    state_index = api_test_state.get("current_state_index", 0) % len(scenario_list)
    state_name = scenario_list[state_index].get("status", f"state-{state_index}")
    interval = api_test_state.get("cycle_interval_seconds", 5.0)
    next_transition_seconds = None

    if api_test_state.get("active") and isinstance(interval, (int, float)) and interval > 0:
        last_transition = api_test_state.get("last_transition_monotonic", time.monotonic())
        elapsed = max(0.0, time.monotonic() - last_transition)
        next_transition_seconds = round(max(0.0, interval - elapsed), 3)

    return {
        "enabled": bool(api_test_state.get("enabled", False)),
        "active": bool(api_test_state.get("active", False)),
        "state_index": state_index,
        "state_name": state_name,
        "next_transition_seconds": next_transition_seconds,
    }


def _is_api_test_enabled(state: dict) -> bool:
    """Check if API test mode is available.

    Verifies that the api_test state dict exists in application state
    and has a lock available for synchronization.

    Args:
        state: Application state dict.

    Returns:
        True if api_test state is available with lock, False otherwise.
    """
    api_test_state = state.get("api_test")
    return bool(api_test_state and api_test_state.get("lock"))


def _validate_interval_seconds_param(
    interval_seconds: Any,
) -> tuple[Optional[tuple[Response, int]], Optional[float]]:
    """Validate the interval_seconds parameter from request body.

    Type checks that interval_seconds is a numeric type (int or float, but
    not bool). Range checks that the value is positive (> 0).

    Args:
        interval_seconds: Raw value from request body to validate.

    Returns:
        Tuple of (error_response, None) if validation fails,
        or (None, float_value) if validation succeeds.
        Error response is formatted as JSON with code ACTION_INVALID_BODY.
    """
    if not isinstance(interval_seconds, (int, float)) or isinstance(interval_seconds, bool):
        return (
            _build_json_error(
                "ACTION_INVALID_BODY",
                "interval_seconds must be a positive number",
                400,
            ),
            None,
        )
    if interval_seconds <= 0:
        return (
            _build_json_error(
                "ACTION_INVALID_BODY",
                "interval_seconds must be greater than 0",
                400,
            ),
            None,
        )
    return None, float(interval_seconds)


def _execute_api_test_action(
    action: str,
    api_test_state: dict,
    scenario_list: list[dict],
    interval_seconds: Optional[float],
) -> None:
    """Execute API test mode action and update state.

    Updates the api_test_state dict with new values based on the action type.
    Action types:
        - "api-test-start": Enable and activate test mode
        - "api-test-stop": Enable but deactivate test mode
        - "api-test-reset": Enable test mode, reset to first scenario
        - "api-test-step": Enable test mode, advance to next scenario

    If interval_seconds is provided, also updates the cycle interval.

    Args:
        action: Normalized action string (one of api-test-*).
        api_test_state: API test state dict to update (must have lock held).
        scenario_list: List of scenario dicts for state cycling.
        interval_seconds: Optional cycle interval in seconds (> 0).
    """
    api_test_state["scenario_list"] = scenario_list
    if interval_seconds is not None:
        api_test_state["cycle_interval_seconds"] = interval_seconds

    if action == "api-test-start":
        api_test_state["enabled"] = True
        api_test_state["active"] = True
        api_test_state["last_transition_monotonic"] = time.monotonic()
    elif action == "api-test-stop":
        api_test_state["enabled"] = True
        api_test_state["active"] = False
    elif action == "api-test-reset":
        api_test_state["enabled"] = True
        api_test_state["active"] = False
        api_test_state["current_state_index"] = 0
        api_test_state["last_transition_monotonic"] = time.monotonic()
    elif action == "api-test-step":
        api_test_state["enabled"] = True
        api_test_state["active"] = False
        api_test_state["current_state_index"] = (
            api_test_state.get("current_state_index", 0) + 1
        ) % len(scenario_list)
        api_test_state["last_transition_monotonic"] = time.monotonic()


class StreamResponseBuilder:
    """Builder for MJPEG stream responses with connection tracking.

    Encapsulates stream response generation with automatic connection slot
    management. Tracks active stream connections and enforces maximum
    connection limits.
    """

    def __init__(self, state: dict, tracker: Any, max_stream_connections: int) -> None:
        """Initialize stream response builder.

        Args:
            state: Application state dict with recording_started, output buffer.
            tracker: ConnectionTracker instance for slot management.
            max_stream_connections: Maximum allowed concurrent connections.
        """
        self.state = state
        self.tracker = tracker
        self.max_stream_connections = max_stream_connections

    def build(self) -> Response:
        """Build and return MJPEG stream response.

        Checks that camera is ready and tries to acquire a connection slot.
        Yields MJPEG frames from output buffer with automatic slot release
        on stream close via try/finally.

        Returns:
            Flask Response object with MJPEG stream or error.
        """
        if not self.state["recording_started"].is_set():
            return Response("Camera stream not ready.", status=503)

        if not self.tracker.try_increment(self.max_stream_connections):
            return Response("Too many connections", status=429)

        slot_release_lock = Lock()
        slot_released = False

        def release_stream_slot() -> None:
            nonlocal slot_released
            with slot_release_lock:
                if slot_released:
                    return
                self.tracker.decrement()
                slot_released = True

        def gen_with_tracking():  # type: ignore
            try:
                output = self.state["output"]
                while True:
                    with output.condition:
                        output.condition.wait(timeout=5)
                        frame = output.frame
                    if frame is None:
                        continue
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            finally:
                release_stream_slot()

        response = Response(
            gen_with_tracking(), mimetype="multipart/x-mixed-replace; boundary=frame"
        )
        # Prevent nginx from buffering the MJPEG stream, which would delay frames.
        response.headers["X-Accel-Buffering"] = "no"
        response.call_on_close(release_stream_slot)
        return response


class SnapshotResponseBuilder:
    """Builder for JPEG snapshot responses.

    Encapsulates snapshot response generation from the current frame buffer.
    """

    def __init__(self, state: dict) -> None:
        """Initialize snapshot response builder.

        Args:
            state: Application state dict with output buffer and recording_started.
        """
        self.state = state

    def build(self) -> Response:
        """Build and return JPEG snapshot response.

        Gets current frame from output buffer. Returns 503 if camera not ready
        or if no frame available yet.

        Returns:
            Flask Response object with JPEG image or error.
        """
        if not self.state["recording_started"].is_set():
            return Response("Camera is not ready yet.", status=503)

        output = self.state["output"]
        with output.condition:
            frame = output.frame

        if frame is None:
            return Response("No camera frame available yet.", status=503)

        return Response(frame, mimetype="image/jpeg")


class WebcamActionHandler:
    """Handler for webcam control plane actions.

    Processes action requests for restart, API test mode, etc.
    with validation and error handling.
    """

    def __init__(self, state: dict) -> None:
        """Initialize action handler.

        Args:
            state: Application state dict with api_test state.
        """
        self.state = state

    def handle_action(self, action: str) -> Response | Tuple[Response, int]:
        """Handle webcam action request.

        Processes normalized action with request body parsing, validation,
        and API test state management.

        Args:
            action: Action name from URL path (e.g., 'restart', 'api-test-start').

        Returns:
            Flask response (Response or tuple of Response and status code).
        """
        normalized_action = action.strip().lower()
        body, body_error = _parse_action_body()
        if body_error is not None:
            return body_error  # type: ignore[return-value]

        if normalized_action == "restart":
            return _build_json_error(
                "ACTION_NOT_IMPLEMENTED",
                "action 'restart' is recognized but not implemented",
                501,
            )

        if normalized_action in {
            "api-test-start",
            "api-test-stop",
            "api-test-reset",
            "api-test-step",
        }:
            if not _is_api_test_enabled(self.state):
                return _build_json_error(
                    "ACTION_UNSUPPORTED",
                    f"action '{normalized_action}' is not supported",
                    400,
                )

            interval_seconds = body.get("interval_seconds") if body else None
            if interval_seconds is not None:
                error, validated_interval = _validate_interval_seconds_param(interval_seconds)
                if error is not None:
                    return error  # type: ignore[return-value]
                interval_seconds = validated_interval

            api_test_state = self.state.get("api_test")
            with api_test_state["lock"]:  # type: ignore[index]
                existing_scenarios = (
                    api_test_state.get("scenario_list") or _DEFAULT_API_TEST_SCENARIOS
                )
                if not isinstance(existing_scenarios, list) or not existing_scenarios:
                    existing_scenarios = _DEFAULT_API_TEST_SCENARIOS

                scenario_order = body.get("scenario_order") if body else None
                scenario_list, scenario_error = _build_api_test_scenario_list(
                    existing_scenarios, scenario_order
                )
                if scenario_error is not None:
                    return scenario_error

                _execute_api_test_action(
                    normalized_action, api_test_state, scenario_list, interval_seconds
                )  # type: ignore[arg-type]

                return jsonify(
                    {
                        "ok": True,
                        "action": normalized_action,
                        "api_test": _get_api_test_runtime_info(api_test_state, scenario_list),  # type: ignore[arg-type]
                    }
                )

        return _build_json_error(
            "ACTION_UNSUPPORTED",
            f"action '{normalized_action or action}' is not supported",
            400,
        )


def _register_stream_routes(app: Flask, builder: StreamResponseBuilder) -> None:
    """Register MJPEG stream and snapshot endpoints.

    Args:
        app: Flask application instance.
        builder: StreamResponseBuilder instance for stream generation.
    """

    @app.route("/stream.mjpg")
    def video_feed() -> Response:
        return builder.build()

    @app.route("/snapshot.jpg")
    def snapshot() -> Response:
        builder_snapshot = SnapshotResponseBuilder(builder.state)
        return builder_snapshot.build()


def _register_action_routes(app: Flask, handler: WebcamActionHandler) -> None:
    """Register control plane action endpoint.

    Args:
        app: Flask application instance.
        handler: WebcamActionHandler instance for action processing.
    """

    @app.route("/api/actions/<action>", methods=["POST"])
    def webcam_action(action: str) -> Response | Tuple[Response, int]:
        """Handle webcam mode control plane actions."""
        return handler.handle_action(action)


def _register_compat_routes(app: Flask, builder: StreamResponseBuilder) -> None:
    """Register OctoPrint compatibility routes.

    Args:
        app: Flask application instance.
        builder: StreamResponseBuilder instance for stream generation.
    """

    @app.route("/webcam")
    @app.route("/webcam/")
    def octoprint_compat_webcam() -> Response:
        action = request.args.get("action", "").strip().lower()
        # Normalize malformed action values: strip anything after ? or & to handle legacy cache busters
        action = action.split("?")[0].split("&")[0]
        if action == "stream":
            return builder.build()
        if action == "snapshot":
            builder_snapshot = SnapshotResponseBuilder(builder.state)
            return builder_snapshot.build()
        return Response("Unsupported action", status=400)


def register_webcam_routes(app: Flask, state: dict) -> None:
    """Register webcam mode Flask routes for MJPEG streaming.

    Registers /stream.mjpg, /snapshot.jpg, /api/actions/<action>, and
    OctoPrint compatibility endpoints (/webcam) that
    serve MJPEG video stream from the frame buffer with connection tracking
    and max connection limits.

    Uses builder pattern to encapsulate stream/snapshot logic and handler
    pattern for action processing.

    Args:
        app: Flask application instance.
        state: Application state dict with frame buffer, tracker, stream stats, etc.
    """
    tracker = state["connection_tracker"]
    max_stream_connections = state["max_stream_connections"]

    # Initialize builders
    stream_builder = StreamResponseBuilder(state, tracker, max_stream_connections)
    action_handler = WebcamActionHandler(state)

    # Register all endpoint groups
    _register_stream_routes(app, stream_builder)
    _register_action_routes(app, action_handler)
    _register_compat_routes(app, stream_builder)


def register_management_camera_error_routes(app: Flask) -> None:
    @app.route("/stream.mjpg")
    @app.route("/snapshot.jpg")
    def camera_routes_disabled() -> Response:
        return Response("Camera endpoints are disabled in management mode.", status=404)
