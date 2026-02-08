import io
import logging
import time
from collections import deque
from threading import Condition, Lock
from typing import Any, Callable, Dict, Optional, Tuple

from flask import Flask, Response, request


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
        with self._lock:
            frame_count = self._frame_count
            last_frame_time = self._last_frame_monotonic
            frame_times = list(self._frame_times_monotonic)
        if len(frame_times) < 2:
            return frame_count, last_frame_time, 0.0
        span = frame_times[-1] - frame_times[0]
        fps = 0.0 if span == 0 else (len(frame_times) - 1) / span
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
                if now - self._last_frame_monotonic < self._target_frame_interval:
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


def register_webcam_routes(
    app: Flask, state: dict, is_flag_enabled: Callable[[str], bool], log_event: Callable[..., None]
) -> None:
    output = state["output"]
    tracker = state["connection_tracker"]

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


def register_management_camera_error_routes(app: Flask) -> None:
    @app.route("/stream.mjpg")
    @app.route("/snapshot.jpg")
    def camera_routes_disabled() -> Response:
        return Response("Camera endpoints are disabled in management mode.", status=404)
