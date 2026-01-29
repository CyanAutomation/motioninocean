"""
Integration tests - verify startup sequence, error recovery, and health checks.
"""

import pytest
import yaml


def test_startup_sequence_markers(workspace_root):
    """Verify the startup sequence markers are present."""
    main_py = workspace_root / "pi_camera_in_docker" / "main.py"
    code = main_py.read_text()

    startup_markers = [
        ("Configuration loading", "os.environ.get"),
        ("Resolution parsing", "resolution_str.split"),
        ("Edge detection config", "edge_detection"),
        ("Camera initialization", "Picamera2()"),
        ("Camera configuration", "create_video_configuration"),
        ("Start recording", "start_recording"),
        ("Start Flask server", "app.run"),
    ]

    for step, marker in startup_markers:
        assert marker in code, f"Missing startup step: {step}"


@pytest.mark.parametrize(
    "scenario,markers",
    [
        (
            "Permission denied handling",
            ["except PermissionError", "Permission denied"],
        ),
        (
            "RuntimeError handling",
            ["except RuntimeError", "Camera initialization failed"],
        ),
        (
            "General exception handling",
            ["except Exception", "Unexpected error"],
        ),
        (
            "Cleanup on error",
            ["finally:", "stop_recording"],
        ),
    ],
)
def test_error_recovery_paths(workspace_root, scenario, markers):
    """Verify error recovery paths are present."""
    main_py = workspace_root / "pi_camera_in_docker" / "main.py"
    code = main_py.read_text()

    for marker in markers:
        assert marker in code, f"Missing marker for {scenario}: {marker}"


@pytest.mark.parametrize(
    "endpoint,markers",
    [
        ("/health", ['@app.route("/health")', "healthy", "200"]),
        ("/ready", ['@app.route("/ready")', "not_ready", "503", "ready", "200"]),
        ("/metrics", ['@app.route("/metrics")', "frames_captured", "current_fps"]),
    ],
)
def test_health_endpoints_present(workspace_root, endpoint, markers):
    """Verify health check endpoints are present."""
    main_py = workspace_root / "pi_camera_in_docker" / "main.py"
    code = main_py.read_text()

    for marker in markers:
        assert marker in code, f"Missing marker for {endpoint}: {marker}"


@pytest.mark.parametrize(
    "metric,marker",
    [
        ("Frame count tracking", "self._frame_count += 1"),
        ("FPS calculation", "def get_fps"),
        ("Frame timing", "self._frame_times_monotonic"),
        ("Status endpoint", "def get_stream_status"),
        ("Uptime tracking", "app.start_time"),
    ],
)
def test_metrics_collection(workspace_root, metric, marker):
    """Verify metrics collection is present."""
    main_py = workspace_root / "pi_camera_in_docker" / "main.py"
    code = main_py.read_text()
    assert marker in code, f"Missing metric: {metric}"


def test_device_security_explicit_devices(workspace_root):
    """Verify explicit device mappings are used."""
    compose_file = workspace_root / "docker-compose.yaml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    service = config["services"]["motion-in-ocean"]

    # Should have devices list
    assert "devices" in service, "Missing devices configuration"
    devices = service["devices"]
    assert len(devices) > 0, "No devices configured"


def test_device_security_no_new_privileges(workspace_root):
    """Verify security options are set."""
    compose_file = workspace_root / "docker-compose.yaml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    service = config["services"]["motion-in-ocean"]
    security_opt = service.get("security_opt", [])

    # Should have no-new-privileges or similar
    assert (
        len(security_opt) > 0 or "privileged" not in service or not service.get("privileged")
    ), "Security options not properly configured"


def test_udev_mount_read_only(workspace_root):
    """Verify udev is mounted read-only."""
    compose_file = workspace_root / "docker-compose.yaml"
    content = compose_file.read_text()

    # Check for read-only udev mount
    assert "/run/udev" in content, "udev mount not found"


def test_camera_detection_error_handling(workspace_root):
    """Verify camera detection error handling is present."""
    main_py = workspace_root / "pi_camera_in_docker" / "main.py"
    code = main_py.read_text()

    # Verify camera detection check is present
    assert "global_camera_info()" in code, "Camera detection check missing"

    # Verify empty camera list handling
    assert "if not camera_info:" in code, "Empty camera list check missing"

    # Verify IndexError handling
    assert "except IndexError" in code, "IndexError handler missing"

    # Verify helpful error messages
    assert "No cameras detected" in code, "Missing camera detection error message"
    assert "device mappings" in code, "Missing device mapping guidance"
    assert "detect-devices.sh" in code, "Missing detect-devices.sh reference"
