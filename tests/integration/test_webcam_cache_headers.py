"""Integration tests for live webcam response cache headers."""

from threading import Event

import pytest
from flask import Flask

from pi_camera_in_docker.modes.webcam import (
    ConnectionTracker,
    FrameBuffer,
    StreamStats,
    register_webcam_routes,
)


EXPECTED_CACHE_CONTROL = "no-store, no-cache, must-revalidate, max-age=0"


def _build_client(*, ready: bool, frame: bytes | None = None, max_connections: int = 1):
    """Build a test client with deterministic webcam route state.

    Args:
        ready: Whether the simulated webcam has started recording.
        frame: Optional JPEG bytes exposed as the latest frame.
        max_connections: Maximum number of concurrent MJPEG streams.

    Returns:
        A Flask test client configured with webcam routes.
    """
    app = Flask(__name__)
    recording_started = Event()
    if ready:
        recording_started.set()

    output = FrameBuffer(StreamStats())
    output.frame = frame
    state = {
        "recording_started": recording_started,
        "output": output,
        "connection_tracker": ConnectionTracker(),
        "max_stream_connections": max_connections,
    }
    register_webcam_routes(app, state)
    return app.test_client()


def _assert_not_cacheable(response) -> None:
    """Assert a response uses the live-data cache policy.

    Args:
        response: Flask test response to inspect.
    """
    assert response.headers["Cache-Control"] == EXPECTED_CACHE_CONTROL


def test_stream_route_success_disables_caching_and_proxy_buffering():
    """A successful MJPEG response is never cached or buffered by nginx."""
    response = _build_client(ready=True, frame=b"jpeg").get("/stream.mjpg", buffered=False)

    assert response.status_code == 200
    _assert_not_cacheable(response)
    assert response.headers["X-Accel-Buffering"] == "no"
    response.close()


@pytest.mark.parametrize(
    ("ready", "max_connections", "expected_status"),
    [(False, 1, 503), (True, 0, 429)],
)
def test_stream_route_transient_errors_disable_caching(
    ready: bool, max_connections: int, expected_status: int
):
    """Camera readiness and connection-limit errors are never cached."""
    response = _build_client(ready=ready, max_connections=max_connections).get("/stream.mjpg")

    assert response.status_code == expected_status
    _assert_not_cacheable(response)


def test_snapshot_route_success_disables_caching():
    """A successful JPEG snapshot is never cached."""
    response = _build_client(ready=True, frame=b"jpeg").get("/snapshot.jpg")

    assert response.status_code == 200
    assert response.data == b"jpeg"
    _assert_not_cacheable(response)


@pytest.mark.parametrize(("ready", "frame"), [(False, None), (True, None)])
def test_snapshot_route_transient_errors_disable_caching(ready: bool, frame: bytes | None):
    """Snapshot readiness and missing-frame errors are never cached."""
    response = _build_client(ready=ready, frame=frame).get("/snapshot.jpg")

    assert response.status_code == 503
    _assert_not_cacheable(response)
