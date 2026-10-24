# Testing

Run the full Python suite with `make test`. The camera paths have two hardware-free test options:

## Stream and deployment smoke tests

Set `MIO_MOCK_CAMERA=true` or use the mock Compose overlay to start webcam mode without camera
hardware. The app generates a synthetic JPEG at the configured frame rate and sends it through the
normal `FrameBuffer` and MJPEG stream route. This checks stream availability, status metrics, and the
web UI against a running app. It bypasses Picamera2 initialization.

## Picamera2 startup and lifecycle tests

Unit tests can exercise the real camera initialization function without importing Picamera2 or
using hardware. `tests/fake_camera.py` provides `build_fake_camera_components`, a deterministic
Picamera2 double that records the requested configuration, emits a supplied frame, and can fail at
each startup stage. See `tests/test_camera_fake.py` for examples covering configuration, frame
delivery, shutdown, and startup cleanup.

When a test truly requires Picamera2 and physical camera hardware, mark it with
`@pytest.mark.requires_camera_hardware`. The test suite skips only marked tests when Picamera2 or
camera device nodes are unavailable; tests using mock or fake cameras still run in regular CI.
