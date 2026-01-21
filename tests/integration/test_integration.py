"""
Integration test verification for motion-in-ocean.
Validates expected behavior and startup flow.
"""

import pytest
import subprocess
from pathlib import Path


@pytest.mark.integration
def test_docker_compose_validation():
    """Test if docker-compose can validate the configuration."""
    compose_file = Path(__file__).parent.parent.parent / 'docker-compose.yml'
    
    try:
        result = subprocess.run(
            ['docker-compose', 'config'],
            capture_output=True,
            text=True,
            cwd=str(compose_file.parent),
            timeout=30
        )
        
        if result.returncode == 0:
            assert 'motion-in-ocean' in result.stdout, \
                "Service name 'motion-in-ocean' not found in docker-compose config"
        else:
            pytest.fail(f"docker-compose validation failed: {result.stderr}")
            
    except FileNotFoundError:
        pytest.skip("Docker Compose not installed")
    except subprocess.TimeoutExpired:
        pytest.fail("docker-compose config command timed out")


@pytest.mark.integration
def test_startup_sequence():
    """Verify the startup sequence is correct."""
    main_py = Path(__file__).parent.parent.parent / 'pi_camera_in_docker' / 'main.py'
    
    with open(main_py, 'r') as f:
        code = f.read()
    
    # Expected startup markers
    startup_markers = [
        "logging.basicConfig",
        "os.environ.get",
        "apply_edge_detection",
        "class StreamingOutput",
        "app = Flask",
        "@app.route",
        "if __name__ == '__main__':",
        "Picamera2()",
        "create_video_configuration",
        "start_recording",
        "app.run",
    ]
    
    for marker in startup_markers:
        assert marker in code, f"Missing startup marker: {marker}"


@pytest.mark.integration
def test_error_recovery_paths():
    """Verify error recovery paths."""
    main_py = Path(__file__).parent.parent.parent / 'pi_camera_in_docker' / 'main.py'
    
    with open(main_py, 'r') as f:
        code = f.read()
    
    # Permission denied error handling
    assert 'except PermissionError' in code, "Missing PermissionError handling"
    assert 'Ensure the container has proper device access' in code or \
           'device access' in code, "Missing permission error message"
    
    # Camera initialization error handling
    assert 'except RuntimeError' in code, "Missing RuntimeError handling"
    
    # Edge detection error handling
    assert 'except Exception as e:' in code, "Missing general exception handling"
    assert 'logger.error' in code, "Missing error logging"
    
    # Clean shutdown
    assert 'finally:' in code, "Missing finally block for cleanup"
    assert 'stop_recording' in code, "Missing stop_recording in cleanup"


@pytest.mark.integration
def test_health_endpoints():
    """Verify health check endpoints."""
    main_py = Path(__file__).parent.parent.parent / 'pi_camera_in_docker' / 'main.py'
    
    with open(main_py, 'r') as f:
        code = f.read()
    
    # /health endpoint (liveness)
    assert "@app.route('/health')" in code, "Missing /health route"
    assert 'healthy' in code, "Missing healthy status in /health"
    
    # /ready endpoint (readiness)
    assert "@app.route('/ready')" in code, "Missing /ready route"
    assert 'ready' in code, "Missing ready status in /ready"
    
    # /metrics endpoint (monitoring)
    assert "@app.route('/metrics')" in code, "Missing /metrics route"
    assert 'frames_captured' in code, "Missing frames_captured in metrics"
    assert 'current_fps' in code or 'get_fps' in code, "Missing FPS in metrics"
    
    # /stream.mjpg endpoint (actual stream)
    assert "@app.route('/stream.mjpg')" in code, "Missing /stream.mjpg route"
    assert 'multipart/x-mixed-replace' in code, "Missing multipart stream content type"


@pytest.mark.integration
def test_metrics_collection():
    """Verify metrics collection."""
    main_py = Path(__file__).parent.parent.parent / 'pi_camera_in_docker' / 'main.py'
    
    with open(main_py, 'r') as f:
        code = f.read()
    
    assert 'self.frame_count += 1' in code, "Missing frame count tracking"
    assert 'self.get_fps()' in code or 'get_fps' in code, "Missing FPS calculation"
    assert 'self.frame_times' in code, "Missing frame timing"
    assert 'def get_status(self)' in code, "Missing status method"
    assert 'app.start_time' in code or 'start_time' in code, "Missing uptime tracking"


@pytest.mark.integration
def test_device_security():
    """Verify device access security."""
    compose_file = Path(__file__).parent.parent.parent / 'docker-compose.yml'
    
    with open(compose_file, 'r') as f:
        compose = f.read()
    
    # Should use explicit devices
    assert 'devices:' in compose, "Missing explicit devices configuration"
    assert '/dev/dma_heap' in compose, "Missing /dev/dma_heap device"
    assert '/dev/vchiq' in compose, "Missing /dev/vchiq device"
    assert '/dev/video' in compose, "Missing /dev/video* devices"
    
    # Healthcheck configured
    assert 'healthcheck:' in compose, "Missing healthcheck configuration"
    assert '/health' in compose, "Missing /health endpoint in healthcheck"
    
    # Check if privileged mode is disabled (should be commented)
    if 'privileged: true' in compose:
        assert '# privileged: true' in compose, \
            "privileged mode should be commented out"


@pytest.mark.integration
def test_dockerfile_device_dependencies():
    """Verify Dockerfile has required device dependencies."""
    dockerfile = Path(__file__).parent.parent.parent / 'Dockerfile'
    
    with open(dockerfile, 'r') as f:
        content = f.read()
    
    # Required packages for camera access (either via apt or pip requirements)
    assert 'python3-libcamera' in content or 'libcamera' in content or \
           'requirements.txt' in content, "Missing libcamera or requirements.txt"
    assert 'python3-opencv' in content or 'opencv' in content, \
        "Missing OpenCV for image processing"


@pytest.mark.integration
def test_docker_compose_config_validation():
    """Validate docker-compose config produces valid output."""
    compose_file = Path(__file__).parent.parent.parent / 'docker-compose.yml'
    
    # Check if docker-compose is available
    try:
        subprocess.run(['docker-compose', '--version'], 
                      capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Docker Compose not installed")
    
    result = subprocess.run(
        ['docker-compose', '-f', str(compose_file), 'config'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should exit successfully
    assert result.returncode == 0, f"docker-compose config failed: {result.stderr}"
    
    # Should contain service definition
    assert 'motion-in-ocean' in result.stdout
