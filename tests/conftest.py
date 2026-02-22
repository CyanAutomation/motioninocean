"""
Pytest configuration and shared fixtures.
"""

import sys
from pathlib import Path

import pytest


# Add the workspace root and app directory to path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
APP_DIR = Path(__file__).parent.parent / "pi_camera_in_docker"
sys.path.insert(0, str(APP_DIR))
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def app_dir():
    """Return the absolute path to the application directory."""
    return APP_DIR


@pytest.fixture
def workspace_root():
    """Return the absolute path to the workspace root."""
    return WORKSPACE_ROOT


@pytest.fixture
def tmp_app_settings_path(tmp_path):
    """Return path to temporary application settings file."""
    return tmp_path / "application-settings.json"


@pytest.fixture
def full_config(tmp_app_settings_path):
    """Return complete config dict with all required runtime keys."""
    return {
        "app_mode": "webcam",
        "resolution": (640, 480),
        "fps": 24,
        "target_fps": 24,
        "jpeg_quality": 90,
        "max_frame_age_seconds": 10.0,
        "max_stream_connections": 10,
        "api_test_mode_enabled": False,
        "api_test_cycle_interval_seconds": 1.0,
        "discovery_enabled": False,
        "discovery_management_url": "http://localhost:8001",
        "discovery_token": "test-token",
        "discovery_interval_seconds": 60,
        "discovery_webcam_id": "test-node",
        "log_level": "INFO",
        "log_format": "text",
        "log_include_identifiers": False,
        "cors_enabled": False,
        "cors_origins": "",
        "bind_host": "127.0.0.1",
        "bind_port": 8000,
        "base_url": "http://localhost:8000",
        "pi3_profile_enabled": False,
        "mock_camera": True,
        "allow_pykms_mock": False,
        "node_registry_path": "/tmp/node-registry.json",
        "application_settings_path": str(tmp_app_settings_path),
        "management_auth_token": "",
        "webcam_control_plane_auth_token": "",
    }


def pytest_collection_modifyitems(config, items):
    """
    Skip tests that require unavailable dependencies or specific environments.

    This allows tests to gracefully skip in CI environments where picamera2
    or docker-compose.yaml are not available, instead of failing at collection time.
    """
    # Check if picamera2 is available
    try:
        import picamera2  # noqa: F401

        has_picamera2 = True
    except (ModuleNotFoundError, ImportError):
        has_picamera2 = False

    # Check if docker-compose.yaml exists
    docker_compose_exists = (WORKSPACE_ROOT / "docker-compose.yaml").exists()

    skip_no_camera = pytest.mark.skip(reason="picamera2 not available")
    skip_no_docker_compose = pytest.mark.skip(reason="docker-compose.yaml not found")

    for item in items:
        # Skip camera/picamera2-dependent tests if picamera2 is not available
        if not has_picamera2:
            test_name = item.nodeid.lower()
            # Skip tests that explicitly require camera hardware
            if any(
                keyword in test_name
                for keyword in [
                    "camera",
                    "picamera2",
                    "real_camera",
                    "init_real_camera",
                    "run_webcam_mode",
                    "webcam_mode_env",
                    "management_mode_boots",
                    "shutdown_camera",
                ]
            ):
                item.add_marker(skip_no_camera)

        # Skip docker integration tests if docker-compose.yaml doesn't exist
        if not docker_compose_exists:
            test_name = item.nodeid.lower()
            if any(
                keyword in test_name
                for keyword in ["device_security", "udev_mount", "docker-compose"]
            ):
                item.add_marker(skip_no_docker_compose)
