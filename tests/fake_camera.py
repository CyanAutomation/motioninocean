"""Deterministic Picamera2 doubles for hardware-free lifecycle tests."""

from typing import Any, NamedTuple, Optional


class FakeCameraComponents(NamedTuple):
    """Fake Picamera2 API classes and the instances created by the app."""

    picamera2_class: type
    jpeg_encoder_class: type
    file_output_class: type
    instances: list[Any]


def build_fake_camera_components(
    *,
    frame_bytes: bytes = b"\xff\xd8fake-camera-frame",
    camera_info: Optional[list[dict[str, str]]] = None,
    failure_stage: Optional[str] = None,
) -> FakeCameraComponents:
    """Build isolated fake Picamera2 classes for one test.

    The fake camera exposes the methods used by webcam startup, can emit a
    deterministic JPEG through the configured output, and can fail at a
    selected startup stage.

    Args:
        frame_bytes: Frame to emit through the app's output during recording.
        camera_info: Camera inventory returned by ``global_camera_info``.
        failure_stage: Optional startup method to fail in. Supported values are
            ``create_video_configuration``, ``configure``, and ``start_recording``.

    Returns:
        Fake camera classes and a list collecting their instances.
    """
    inventory = [{"id": "fake-camera-0"}] if camera_info is None else camera_info
    instances: list[Any] = []

    def fail_at(stage: str) -> None:
        if failure_stage == stage:
            raise RuntimeError(f"fake camera failed at {stage}")

    class FakeJpegEncoder:
        """Record the quality requested by the application."""

        def __init__(self, q: int) -> None:
            self.quality = q

    class FakeFileOutput:
        """Forward fake camera bytes into the real stream output."""

        def __init__(self, output: Any) -> None:
            self.output = output

        def write(self, frame: bytes) -> int:
            return self.output.write(frame)

    class FakePicamera2:
        """Implement the Picamera2 startup and recording methods used by the app."""

        def __init__(self) -> None:
            self.started = False
            self.stop_calls = 0
            self.video_configuration: Optional[dict[str, Any]] = None
            self.configured_video_configuration: Optional[dict[str, Any]] = None
            self.encoder: Optional[FakeJpegEncoder] = None
            self.file_output: Optional[FakeFileOutput] = None
            instances.append(self)

        @staticmethod
        def global_camera_info() -> list[dict[str, str]]:
            return list(inventory)

        def create_video_configuration(self, *, main: dict[str, Any]) -> dict[str, Any]:
            fail_at("create_video_configuration")
            self.video_configuration = {"main": main}
            return self.video_configuration

        def configure(self, video_configuration: dict[str, Any]) -> None:
            fail_at("configure")
            self.configured_video_configuration = video_configuration

        def start_recording(self, encoder: FakeJpegEncoder, output: FakeFileOutput) -> None:
            fail_at("start_recording")
            self.encoder = encoder
            self.file_output = output
            self.started = True
            if frame_bytes:
                output.write(frame_bytes)

        def stop_recording(self) -> None:
            self.stop_calls += 1
            self.started = False

    return FakeCameraComponents(
        FakePicamera2,
        FakeJpegEncoder,
        FakeFileOutput,
        instances,
    )
