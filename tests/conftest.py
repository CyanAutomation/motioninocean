"""
Pytest configuration and shared fixtures.
"""

import sys
from pathlib import Path

import pytest


# Add the app directory to path
APP_DIR = Path(__file__).parent.parent / "pi_camera_in_docker"
sys.path.insert(0, str(APP_DIR))


@pytest.fixture
def app_dir():
    """Return the absolute path to the application directory."""
    return APP_DIR


@pytest.fixture
def workspace_root():
    """Return the absolute path to the workspace root."""
    return Path(__file__).parent.parent
