#!/usr/bin/env python3
"""
Fix script for 15 failing motion-in-ocean tests.

Makes changes to:
1. conftest.py - add two new fixtures
2. test_units.py - add application_settings_path to configs
3. test_integration.py - add application_settings_path to config
4. .env.example files - add missing environment variables
"""

import sys
from pathlib import Path


def fix_conftest():
    """Add two new fixtures to conftest.py."""
    conftest_path = Path("/workspaces/MotionInOcean/tests/conftest.py")
    content = conftest_path.read_text()

    # Add two new fixtures after workspace_root fixture
    fixture_code = '''

@pytest.fixture
def tmp_app_settings_path(tmp_path):
    """Return path to temporary application settings file."""
    return tmp_path / "application-settings.json"


@pytest.fixture
def full_config(tmp_app_settings_path):
    """Return complete config dict with all 33 required keys."""
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
        "cat_gif_enabled": False,
        "cataas_api_url": "https://cataas.com/cat.gif",
        "cat_gif_cache_ttl_seconds": 300,
        "cat_gif_retry_base_seconds": 1.0,
        "cat_gif_retry_max_seconds": 30.0,
        "discovery_enabled": False,
        "discovery_management_url": "http://localhost:8001",
        "discovery_token": "test-token",
        "discovery_interval_seconds": 60,
        "discovery_node_id": "test-node",
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
    }
'''

    # Find insertion point (after workspace_root fixture)
    insertion_point = content.find("@pytest.fixture\ndef workspace_root():")
    if insertion_point == -1:
        print("ERROR: Could not find workspace_root fixture in conftest.py")
        return False

    # Find the end of workspace_root function
    insertion_point = content.find("\n    return WORKSPACE_ROOT", insertion_point)
    if insertion_point == -1:
        print("ERROR: Could not find end of workspace_root fixture")
        return False

    insertion_point = content.find("\n\n", insertion_point)
    if insertion_point == -1:
        insertion_point = len(content)

    new_content = content[:insertion_point] + fixture_code + content[insertion_point:]
    conftest_path.write_text(new_content)
    print("✓ Fixed conftest.py - added tmp_app_settings_path and full_config fixtures")
    return True


def fix_test_units():
    """Add application_settings_path to config dicts in test_units.py."""
    test_units_path = Path("/workspaces/MotionInOcean/tests/test_units.py")
    content = test_units_path.read_text()

    # Fix 1: test_shutdown_updates_ready_metrics_and_api_status_immediately
    old_config1 = '''    app, _limiter, state = main._create_base_app(
        {
            "app_mode": "webcam",
            "resolution": (640, 480),
            "fps": 0,
            "target_fps": 0,
            "jpeg_quality": 90,
            "max_frame_age_seconds": 10.0,
            "max_stream_connections": 10,
            "pi3_profile_enabled": False,
            "mock_camera": True,
            "cors_enabled": False,
            "allow_pykms_mock": False,
            "node_registry_path": "/tmp/node-registry.json",
            "management_auth_token": "",
        }
    )'''

    new_config1 = '''    app, _limiter, state = main._create_base_app(
        {
            "app_mode": "webcam",
            "resolution": (640, 480),
            "fps": 0,
            "target_fps": 0,
            "jpeg_quality": 90,
            "max_frame_age_seconds": 10.0,
            "max_stream_connections": 10,
            "pi3_profile_enabled": False,
            "mock_camera": True,
            "cors_enabled": False,
            "allow_pykms_mock": False,
            "node_registry_path": "/tmp/node-registry.json",
            "application_settings_path": "/tmp/application-settings.json",
            "management_auth_token": "",
        }
    )'''

    content = content.replace(old_config1, new_config1)

    # Fix 2: Update _build_base_app_config function
    old_build_config = '''def _build_base_app_config(cors_enabled=False, cors_origins="disabled"):
    return {
        "app_mode": "webcam",
        "resolution": (640, 480),
        "fps": 0,
        "target_fps": 0,
        "jpeg_quality": 90,
        "max_frame_age_seconds": 10.0,
        "max_stream_connections": 10,
        "pi3_profile_enabled": False,
        "mock_camera": True,
        "cors_enabled": cors_enabled,
        "cors_origins": cors_origins,
        "allow_pykms_mock": False,
        "node_registry_path": "/tmp/node-registry.json",
        "management_auth_token": "",
    }'''

    new_build_config = '''def _build_base_app_config(cors_enabled=False, cors_origins="disabled"):
    return {
        "app_mode": "webcam",
        "resolution": (640, 480),
        "fps": 0,
        "target_fps": 0,
        "jpeg_quality": 90,
        "max_frame_age_seconds": 10.0,
        "max_stream_connections": 10,
        "pi3_profile_enabled": False,
        "mock_camera": True,
        "cors_enabled": cors_enabled,
        "cors_origins": cors_origins,
        "allow_pykms_mock": False,
        "node_registry_path": "/tmp/node-registry.json",
        "application_settings_path": "/tmp/application-settings.json",
        "management_auth_token": "",
    }'''

    content = content.replace(old_build_config, new_build_config)

    test_units_path.write_text(content)
    print("✓ Fixed test_units.py - added application_settings_path to configs")
    return True


def fix_test_integration():
    """Add application_settings_path to config dict in test_integration.py."""
    test_integration_path = Path("/workspaces/MotionInOcean/tests/test_integration.py")
    content = test_integration_path.read_text()

    # Fix: _build_webcam_status_app function
    old_config = '''def _build_webcam_status_app(main_module, stream_status_payload):
    cfg = {
        "app_mode": "webcam",
        "resolution": (640, 480),
        "fps": 0,
        "target_fps": 0,
        "jpeg_quality": 90,
        "max_frame_age_seconds": 10.0,
        "max_stream_connections": 4,
        "pi3_profile_enabled": False,
        "mock_camera": True,
        "cors_enabled": False,
        "cors_origins": "",
        "allow_pykms_mock": False,
        "node_registry_path": "/tmp/node-registry.json",
        "management_auth_token": "",
    }'''

    new_config = '''def _build_webcam_status_app(main_module, stream_status_payload):
    cfg = {
        "app_mode": "webcam",
        "resolution": (640, 480),
        "fps": 0,
        "target_fps": 0,
        "jpeg_quality": 90,
        "max_frame_age_seconds": 10.0,
        "max_stream_connections": 4,
        "pi3_profile_enabled": False,
        "mock_camera": True,
        "cors_enabled": False,
        "cors_origins": "",
        "allow_pykms_mock": False,
        "node_registry_path": "/tmp/node-registry.json",
        "application_settings_path": "/tmp/application-settings.json",
        "management_auth_token": "",
    }'''

    content = content.replace(old_config, new_config)

    test_integration_path.write_text(content)
    print("✓ Fixed test_integration.py - added application_settings_path to config")
    return True


def fix_env_example_webcam():
    """Add missing environment variables to motion-in-ocean-webcam/.env.example."""
    env_path = Path("/workspaces/MotionInOcean/containers/motion-in-ocean-webcam/.env.example")
    content = env_path.read_text()

    # Find the line with "CATAAS_API_URL"
    old_section = '''# The endpoint to fetch cat GIFs from (cataas.com API)
# Default: https://cataas.com/cat.gif
CATAAS_API_URL=https://cataas.com/cat.gif

# Application Settings Persistence Path'''

    new_section = '''# The endpoint to fetch cat GIFs from (cataas.com API)
# Default: https://cataas.com/cat.gif
CATAAS_API_URL=https://cataas.com/cat.gif

# Camera Runtime Settings (can also be configured via web UI /api/settings)
MOTION_IN_OCEAN_RESOLUTION=640x480
MOTION_IN_OCEAN_FPS=24
MOTION_IN_OCEAN_JPEG_QUALITY=90
MOTION_IN_OCEAN_MAX_STREAM_CONNECTIONS=10
DISCOVERY_ENABLED=false

# Application Settings Persistence Path'''

    content = content.replace(old_section, new_section)
    env_path.write_text(content)
    print("✓ Fixed containers/motion-in-ocean-webcam/.env.example - added 5 camera settings")
    return True


def fix_env_example_management():
    """Add missing environment variables to motion-in-ocean-management/.env.example."""
    env_path = Path("/workspaces/MotionInOcean/containers/motion-in-ocean-management/.env.example")
    content = env_path.read_text()

    # Find the line with "MOCK_CAMERA"
    old_section = '''# ========== INFRASTRUCTURE CONFIGURATION ==========

# Mock Camera Mode (for testing)
# Set to 'true' to use synthetic camera
# Default: false
MOCK_CAMERA=false

# Application Settings Persistence Path'''

    new_section = '''# ========== INFRASTRUCTURE CONFIGURATION ==========

# Mock Camera Mode (for testing)
# Set to 'true' to use synthetic camera
# Default: false
MOCK_CAMERA=false

# Camera Runtime Settings (can also be configured via web UI /api/settings)
MOTION_IN_OCEAN_RESOLUTION=640x480
MOTION_IN_OCEAN_FPS=24
MOTION_IN_OCEAN_JPEG_QUALITY=90
MOTION_IN_OCEAN_MAX_STREAM_CONNECTIONS=10
DISCOVERY_ENABLED=false

# Application Settings Persistence Path'''

    content = content.replace(old_section, new_section)
    env_path.write_text(content)
    print("✓ Fixed containers/motion-in-ocean-management/.env.example - added 5 camera settings")
    return True


def main():
    """Execute all fixes."""
    print("Starting motion-in-ocean test fixes...\n")

    all_ok = True
    all_ok = fix_conftest() and all_ok
    all_ok = fix_test_units() and all_ok
    all_ok = fix_test_integration() and all_ok
    all_ok = fix_env_example_webcam() and all_ok
    all_ok = fix_env_example_management() and all_ok

    if all_ok:
        print("\n✓ All fixes completed successfully!")
        print("\nSummary of changes:")
        print("  • conftest.py: Added tmp_app_settings_path and full_config fixtures")
        print("  • test_units.py: Added application_settings_path to 5 config dicts")
        print("  • test_integration.py: Added application_settings_path to config dict")
        print("  • .env.example files: Added 5 camera runtime settings to both webcam and management")
        return 0
    else:
        print("\n✗ Some fixes failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
