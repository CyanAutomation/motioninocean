"""Tests for real-camera lifecycle behavior using a deterministic fake camera."""

from threading import Event, RLock

import pytest

from pi_camera_in_docker import main
from pi_camera_in_docker.modes.webcam import FrameBuffer, StreamStats
from tests.fake_camera import build_fake_camera_components


def _camera_state():
    """Build the minimal state required by camera initialization."""
    stats = StreamStats()
    output = FrameBuffer(stats)
    return {
        "recording_started": Event(),
        "shutdown_requested": Event(),
        "camera_lock": RLock(),
        "output": output,
        "stream_stats": stats,
        "picam2_instance": None,
        "camera_startup_error": None,
    }


def _camera_config():
    """Build valid settings for the real camera initialization path."""
    return {
        "resolution": (640, 480),
        "jpeg_quality": 83,
        "pykms_mock_fallback_enabled": False,
    }


def _install_fake_camera(monkeypatch, components):
    """Provide fake Picamera2 classes and a deterministic device inventory."""
    monkeypatch.setattr(
        main,
        "import_camera_components",
        lambda _fallback_enabled: (
            components.picamera2_class,
            components.jpeg_encoder_class,
            components.file_output_class,
        ),
    )
    monkeypatch.setattr(
        main,
        "_detect_camera_devices",
        lambda: {
            "video_devices": ["/dev/video-fake"],
            "media_devices": [],
            "v4l_subdev_devices": [],
            "dma_heap_devices": [],
            "vchiq_device": False,
        },
    )


@pytest.mark.parametrize("frame", [b"fake-jpeg-frame", b""])
def test_real_camera_lifecycle_with_fake_camera(monkeypatch, frame):
    """Camera setup sends deterministic frames through the normal FrameBuffer."""
    components = build_fake_camera_components(frame_bytes=frame)
    _install_fake_camera(monkeypatch, components)
    state = _camera_state()

    main._init_real_camera(state, _camera_config())

    camera = components.instances[0]
    assert camera.video_configuration == {"main": {"size": (640, 480), "format": "BGR888"}}
    assert camera.configured_video_configuration == camera.video_configuration
    assert camera.encoder.quality == 83
    assert camera.file_output.output is state["output"]
    assert state["output"].frame == frame
    assert state["stream_stats"].snapshot()[0] == 1
    assert camera.started is True
    assert state["recording_started"].is_set()
    assert state["camera_startup_error"] is None

    main._shutdown_camera(state)

    assert camera.stop_calls == 1
    assert camera.started is False
    assert state["picam2_instance"] is None
    assert state["shutdown_requested"].is_set()
    assert not state["recording_started"].is_set()


@pytest.mark.parametrize(
    "failure_stage", ["create_video_configuration", "configure", "start_recording"]
)
def test_real_camera_startup_failure_cleans_up_fake_camera(monkeypatch, failure_stage):
    """Camera startup failures leave recording stopped and publish a useful error."""
    components = build_fake_camera_components(failure_stage=failure_stage)
    _install_fake_camera(monkeypatch, components)
    state = _camera_state()

    main._init_real_camera(state, _camera_config())

    assert not state["recording_started"].is_set()
    assert state["shutdown_requested"].is_set()
    assert state["picam2_instance"] is None
    assert state["camera_startup_error"]["code"] == "CAMERA_STARTUP_FAILED"
    assert failure_stage in state["camera_startup_error"]["message"]

    if failure_stage == "start_recording":
        assert components.instances[0].stop_calls == 0
