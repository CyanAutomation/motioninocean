"""
pytest configuration and fixtures for motion-in-ocean tests.

This file provides common fixtures and configurations for all tests.
"""

import pytest
import os
from typing import Generator


@pytest.fixture
def mock_env_vars() -> Generator[None, None, None]:
    """Set up mock environment variables for testing."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ['RESOLUTION'] = '640x480'
    os.environ['FPS'] = '30'
    os.environ['EDGE_DETECTION'] = 'false'
    os.environ['MOCK_CAMERA'] = 'true'
    os.environ['TZ'] = 'UTC'
    os.environ['JPEG_QUALITY'] = '100'
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_env_file(tmp_path):
    """Create a temporary .env file for testing."""
    env_file = tmp_path / ".env"
    env_content = """RESOLUTION=1280x720
FPS=60
EDGE_DETECTION=true
TZ=America/New_York
MOCK_CAMERA=false
JPEG_QUALITY=85
"""
    env_file.write_text(env_content)
    return env_file


@pytest.fixture
def sample_image_data():
    """Provide sample image data for testing."""
    # Simple 10x10 black image in JPEG format (minimal valid JPEG)
    # This is a minimal JPEG file structure
    jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
    jpeg_footer = b'\xff\xd9'
    return jpeg_header + b'\x00' * 100 + jpeg_footer
