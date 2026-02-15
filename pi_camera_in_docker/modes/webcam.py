import io
import logging
import time
from collections import deque
from threading import Condition, Lock
from typing import Any, Callable, Dict, Optional, Tuple

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import BadRequest


logger = logging.getLogger(__name__)


class StreamStats:
    def __init__(self) -> None:
        self._lock = Lock()
        self._frame_count = 0
        self._last_frame_monotonic: Optional[float] = None
        self._frame_times_monotonic: deque[float] = deque(maxlen=30)

    def record_frame(self, monotonic_timestamp: float) -> None:
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
    def __init__(
        self, stats: StreamStats, max_frame_size: Optional[int] = None, target_fps: int = 0
    ) -> None:
        self.frame: Optional[bytes] = None
        self.condition = Condition()
        self._stats = stats
        self._max_frame_size = max_frame_size
        self._target_frame_interval = None if target_fps <= 0 else 1.0 / target_fps
        self._last_frame_monotonic: Optional[float] = None

    def write(self, buf: bytes) -> int:
        size = len(buf)
        if self._max_frame_size is not None and size > self._max_frame_size:
            return size
        with self.condition:
            now = time.monotonic()
            if self._target_frame_interval is not None and self._last_frame_monotonic is not None:
                next_valid_capture_time = self._last_frame_monotonic + self._target_frame_interval
                if now < next_valid_capture_time:
                    logger.debug(
                        f"Frame dropped: now={now:.4f}, last_capture={self._last_frame_monotonic:.4f}, "
                        f"next_valid={next_valid_capture_time:.4f}, diff={now - self._last_frame_monotonic:.4f}, "
                        f"interval={self._target_frame_interval:.4f}"
                    )
                    return size
            self.frame = buf
            self._last_frame_monotonic = now
            self._stats.record_frame(now)
            self.condition.notify_all()
        return size


class ConnectionTracker:
    def __init__(self) -> None:
        self._count = 0
        self._lock = Lock()

    def increment(self) -> int:
        with self._lock:
            self._count += 1
            return self._count

    def try_increment(self, max_connections: int) -> bool:
        with self._lock:
            if self._count >= max_connections:
                return False
            self._count += 1
            return True

    def decrement(self) -> int:
        with self._lock:
            self._count -= 1
            return self._count

    def get_count(self) -> int:
        with self._lock:
            return self._count


def import_camera_components(allow_pykms_mock: bool):
    try:
        from picamera2 import Picamera2
    except (ModuleNotFoundError, AttributeError) as e:
        if allow_pykms_mock and ("pykms" in str(e) or "kms" in str(e) or "PixelFormat" in str(e)):
            import sys
            import types

            pykms_mock = types.ModuleType("pykms")
            kms_mock = types.ModuleType("kms")

            class PixelFormatMock:
                RGB888 = "RGB888"
                XRGB8888 = "XRGB8888"
                BGR888 = "BGR888"
                XBGR8888 = "XBGR8888"

            pykms_mock.PixelFormat = PixelFormatMock
            kms_mock.PixelFormat = PixelFormatMock
            sys.modules["pykms"] = pykms_mock
            sys.modules["kms"] = kms_mock
            from picamera2 import Picamera2
        else:
            raise

    from picamera2.encoders import JpegEncoder
    from picamera2.outputs import FileOutput

    return Picamera2, JpegEncoder, FileOutput


def get_stream_status(stats: StreamStats, resolution: Tuple[int, int]) -> Dict[str, Any]:
    now = time.monotonic()
    frame_count, last_frame_time, current_fps = stats.snapshot()
    age = None if last_frame_time is None else round(now - last_frame_time, 2)
    return {
        "frames_captured": frame_count,
        "current_fps": round(current_fps, 2),
        "resolution": resolution,
        "last_frame_age_seconds": age,
    }


def register_webcam_routes(app: Flask, state: dict, is_flag_enabled: Callable[[str], bool]) -> None:
    output = state["output"]
    tracker = state["connection_tracker"]

    supported_actions = [
        "restart",
        "api-test-start",
        "api-test-stop",
        "api-test-reset",
        "api-test-step",
    ]

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

    def _json_error(code: str, message: str, status_code: int) -> tuple[Response, int]:
        return (
            jsonify(
                {
                    "error": {
                        "code": code,
                        "message": message,
                        "details": {"supported_actions": supported_actions},
                    }
                }
            ),
            status_code,
        )

    def _parse_optional_action_body() -> tuple[Optional[dict], Optional[tuple[Response, int]]]:
        if not request.data:
            return None, None

        try:
            body = request.get_json(silent=False)
        except BadRequest:
            return None, _json_error("ACTION_INVALID_BODY", "request body must be valid JSON", 400)

        if not isinstance(body, dict):
            return None, _json_error(
                "ACTION_INVALID_BODY", "request body must be a JSON object", 400
            )

        allowed_keys = {"interval_seconds", "scenario_order"}
        unknown_keys = sorted(set(body.keys()) - allowed_keys)
        if unknown_keys:
            return None, _json_error(
                "ACTION_INVALID_BODY",
                f"request body contains unsupported keys: {', '.join(unknown_keys)}",
                400,
            )

        return body, None

    def _api_test_runtime_info(api_test_state: dict, scenario_list: list[dict]) -> dict:
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

    def _resolve_api_test_scenarios(
        api_test_state: dict, body: Optional[dict]
    ) -> tuple[Optional[list[dict]], Optional[tuple[Response, int]]]:
        body = body or {}
        existing_scenarios = api_test_state.get("scenario_list") or default_api_test_scenarios
        if not isinstance(existing_scenarios, list) or not existing_scenarios:
            existing_scenarios = default_api_test_scenarios

        scenario_order = body.get("scenario_order")
        if scenario_order is None:
            return existing_scenarios, None
        if not isinstance(scenario_order, list) or not scenario_order:
            return None, _json_error(
                "ACTION_INVALID_BODY", "scenario_order must be a non-empty array", 400
            )
        if not all(isinstance(index, int) for index in scenario_order):
            return None, _json_error(
                "ACTION_INVALID_BODY", "scenario_order must contain only integer indexes", 400
            )

        unique_indexes = set(scenario_order)
        max_index = len(existing_scenarios) - 1
        if unique_indexes != set(range(len(existing_scenarios))):
            return None, _json_error(
                "ACTION_INVALID_BODY",
                f"scenario_order must contain each scenario index exactly once from 0 to {max_index}",
                400,
            )

        return [existing_scenarios[index] for index in scenario_order], None

    def _build_stream_response() -> Response:
        if not state["recording_started"].is_set():
            return Response("Camera stream not ready.", status=503)
        if not tracker.try_increment(state["max_stream_connections"]):
            return Response("Too many connections", status=429)

        slot_release_lock = Lock()
        slot_released = False

        def release_stream_slot() -> None:
            nonlocal slot_released
            with slot_release_lock:
                if slot_released:
                    return
                tracker.decrement()
                slot_released = True

        def gen_with_tracking():
            try:
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
        response.call_on_close(release_stream_slot)
        return response

    def _build_snapshot_response() -> Response:
        if not state["recording_started"].is_set():
            return Response("Camera is not ready yet.", status=503)
        with output.condition:
            frame = output.frame
        if frame is None:
            return Response("No camera frame available yet.", status=503)
        return Response(frame, mimetype="image/jpeg")

    @app.route("/stream.mjpg")
    def video_feed() -> Response:
        return _build_stream_response()

    @app.route("/snapshot.jpg")
    def snapshot() -> Response:
        return _build_snapshot_response()

    @app.route("/api/cat-gif/refresh", methods=["POST"])
    def refresh_cat_gif() -> Response:
        cat_generator = state.get("cat_gif_generator")
        if cat_generator is None:
            return jsonify(
                {
                    "status": "unavailable",
                    "message": "Cat GIF mode is not enabled",
                }
            ), 400
        cat_generator.request_refresh()
        return jsonify(
            {
                "status": "requested",
                "message": "Cat GIF refresh requested; new cat will load on next frame",
            }
        ), 200

    @app.route("/webcam")
    @app.route("/webcam/")
    def octoprint_compat_webcam() -> Response:
        if not is_flag_enabled("OCTOPRINT_COMPATIBILITY"):
            return Response("OctoPrint compatibility routes are disabled.", status=404)
        action = request.args.get("action", "").strip().lower()
        if action == "stream":
            return _build_stream_response()
        if action == "snapshot":
            return _build_snapshot_response()
        return Response("Unsupported action", status=400)

    @app.route("/api/actions/<action>", methods=["POST"])
    def webcam_action(action: str):
        normalized_action = action.strip().lower()
        body, body_error = _parse_optional_action_body()
        if body_error is not None:
            return body_error

        if normalized_action == "restart":
            return _json_error(
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
            api_test_state = state.get("api_test")
            if not api_test_state or not api_test_state.get("lock"):
                return _json_error(
                    "ACTION_UNSUPPORTED",
                    f"action '{normalized_action}' is not supported",
                    400,
                )

            interval_seconds = body.get("interval_seconds") if body else None
            if interval_seconds is not None:
                if not isinstance(interval_seconds, (int, float)) or isinstance(
                    interval_seconds, bool
                ):
                    return _json_error(
                        "ACTION_INVALID_BODY",
                        "interval_seconds must be a positive number",
                        400,
                    )
                if interval_seconds <= 0:
                    return _json_error(
                        "ACTION_INVALID_BODY",
                        "interval_seconds must be greater than 0",
                        400,
                    )

            with api_test_state["lock"]:
                scenario_list, scenario_error = _resolve_api_test_scenarios(api_test_state, body)
                if scenario_error is not None:
                    return scenario_error

                api_test_state["scenario_list"] = scenario_list
                if interval_seconds is not None:
                    api_test_state["cycle_interval_seconds"] = float(interval_seconds)

                if normalized_action == "api-test-start":
                    api_test_state["enabled"] = True
                    api_test_state["active"] = True
                    api_test_state["last_transition_monotonic"] = time.monotonic()
                elif normalized_action == "api-test-stop":
                    api_test_state["enabled"] = True
                    api_test_state["active"] = False
                elif normalized_action == "api-test-reset":
                    api_test_state["enabled"] = True
                    api_test_state["active"] = False
                    api_test_state["current_state_index"] = 0
                    api_test_state["last_transition_monotonic"] = time.monotonic()
                elif normalized_action == "api-test-step":
                    api_test_state["enabled"] = True
                    api_test_state["active"] = False
                    api_test_state["current_state_index"] = (
                        api_test_state.get("current_state_index", 0) + 1
                    ) % len(scenario_list)
                    api_test_state["last_transition_monotonic"] = time.monotonic()

                return jsonify(
                    {
                        "ok": True,
                        "action": normalized_action,
                        "api_test": _api_test_runtime_info(api_test_state, scenario_list),
                    }
                )

        return _json_error(
            "ACTION_UNSUPPORTED",
            f"action '{normalized_action or action}' is not supported",
            400,
        )


def register_management_camera_error_routes(app: Flask) -> None:
    @app.route("/stream.mjpg")
    @app.route("/snapshot.jpg")
    def camera_routes_disabled() -> Response:
        return Response("Camera endpoints are disabled in management mode.", status=404)
