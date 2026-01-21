"""
Unit tests for validating motion-in-ocean configuration and code structure.
Tests docker-compose configuration, Python code syntax, and endpoints.
"""

import pytest
import ast
import yaml
from pathlib import Path


@pytest.mark.unit
def test_python_syntax():
    """Test if main.py has valid Python syntax."""
    main_py = Path(__file__).parent.parent.parent / 'pi_camera_in_docker' / 'main.py'
    
    with open(main_py, 'r') as f:
        code = f.read()
    
    # Should not raise SyntaxError
    ast.parse(code)


@pytest.mark.unit
def test_docker_compose_valid_yaml():
    """Test if docker-compose.yml has valid YAML syntax."""
    compose_file = Path(__file__).parent.parent.parent / 'docker-compose.yml'
    
    with open(compose_file, 'r') as f:
        config = yaml.safe_load(f)
    
    # Verify essential keys
    assert 'services' in config, "Missing 'services' key"
    assert 'motion-in-ocean' in config['services'], "Missing 'motion-in-ocean' service"


@pytest.mark.unit
def test_docker_compose_service_config():
    """Test docker-compose.yml service configuration."""
    compose_file = Path(__file__).parent.parent.parent / 'docker-compose.yml'
    
    with open(compose_file, 'r') as f:
        config = yaml.safe_load(f)
    
    service = config['services']['motion-in-ocean']
    
    # Check required fields
    required_fields = ['image', 'restart', 'ports', 'healthcheck']
    for field in required_fields:
        assert field in service, f"Missing required field: {field}"
    
    # Verify environment variables are configured
    optional_env = ['environment', 'env_file']
    assert any(field in service for field in optional_env), \
        "Missing environment configuration (env_file or environment)"


@pytest.mark.unit
def test_docker_compose_healthcheck():
    """Test docker-compose.yml healthcheck configuration."""
    compose_file = Path(__file__).parent.parent.parent / 'docker-compose.yml'
    
    with open(compose_file, 'r') as f:
        config = yaml.safe_load(f)
    
    healthcheck = config['services']['motion-in-ocean'].get('healthcheck', {})
    
    assert 'test' in healthcheck, "Missing healthcheck test"
    assert '/health' in str(healthcheck.get('test')), \
        "Healthcheck should use /health endpoint"


@pytest.mark.unit
def test_docker_compose_device_mappings():
    """Test docker-compose.yml device mappings."""
    compose_file = Path(__file__).parent.parent.parent / 'docker-compose.yml'
    
    with open(compose_file, 'r') as f:
        config = yaml.safe_load(f)
    
    service = config['services']['motion-in-ocean']
    devices = service.get('devices', [])
    
    assert len(devices) > 0, "No device mappings found"
    assert any('/dev/dma_heap' in str(d) for d in devices), "Missing /dev/dma_heap device"
    assert any('/dev/vchiq' in str(d) for d in devices), "Missing /dev/vchiq device"
    assert any('/dev/video' in str(d) for d in devices), "Missing /dev/video* devices"


@pytest.mark.unit
def test_flask_endpoints_defined():
    """Verify that Flask endpoints are defined in main.py."""
    main_py = Path(__file__).parent.parent.parent / 'pi_camera_in_docker' / 'main.py'
    
    with open(main_py, 'r') as f:
        code = f.read()
    
    endpoints = {
        '@app.route(\'/\')': 'Root endpoint',
        '@app.route(\'/health\')': 'Health check',
        '@app.route(\'/ready\')': 'Readiness probe',
        '@app.route(\'/stream.mjpg\')': 'MJPEG stream',
    }
    
    for route, description in endpoints.items():
        assert route in code, f"Missing {description}: {route}"


@pytest.mark.unit
def test_error_handling():
    """Verify error handling in main.py."""
    main_py = Path(__file__).parent.parent.parent / 'pi_camera_in_docker' / 'main.py'
    
    with open(main_py, 'r') as f:
        code = f.read()
    
    assert 'except PermissionError' in code, "Missing PermissionError handling"
    assert 'except RuntimeError' in code, "Missing RuntimeError handling"
    assert 'except Exception' in code, "Missing general exception handling"
    assert 'finally:' in code, "Missing try-finally block"


@pytest.mark.unit
def test_logging_configuration():
    """Verify logging configuration."""
    main_py = Path(__file__).parent.parent.parent / 'pi_camera_in_docker' / 'main.py'
    
    with open(main_py, 'r') as f:
        code = f.read()
    
    assert 'logging.basicConfig' in code, "Missing logging basicConfig"
    assert 'logger = logging.getLogger' in code, "Missing logger instance"
    assert 'format=' in code, "Missing structured log format"
    assert 'level=logging.INFO' in code, "Missing INFO level"


@pytest.mark.unit
def test_environment_variables():
    """Verify environment variable handling."""
    main_py = Path(__file__).parent.parent.parent / 'pi_camera_in_docker' / 'main.py'
    
    with open(main_py, 'r') as f:
        code = f.read()
    
    env_vars = ['RESOLUTION', 'EDGE_DETECTION', 'FPS']
    
    for var in env_vars:
        assert f'os.environ.get("{var}"' in code or f"os.environ.get('{var}'" in code, \
            f"Missing environment variable: {var}"


@pytest.mark.unit
def test_env_file_exists():
    """Verify .env file exists with required variables."""
    env_file = Path(__file__).parent.parent.parent / '.env'
    
    if not env_file.exists():
        pytest.skip(".env file not found (may be in .gitignore)")
        return
    
    with open(env_file, 'r') as f:
        env_content = f.read()
    
    required_vars = ['TZ', 'RESOLUTION', 'EDGE_DETECTION']
    
    for var in required_vars:
        assert f'{var}=' in env_content, f"Missing {var} in .env"


@pytest.mark.unit
def test_dockerfile_configuration():
    """Basic checks on Dockerfile."""
    dockerfile = Path(__file__).parent.parent.parent / 'Dockerfile'
    
    with open(dockerfile, 'r') as f:
        content = f.read()
    
    checks = {
        'FROM debian:bookworm': 'Base image',
        'python3-flask': 'Python flask',
        'python3-opencv': 'Python opencv',
        'WORKDIR /app': 'Working directory',
        'CMD': 'Entry point',
    }
    
    for pattern, description in checks.items():
        assert pattern in content, f"Missing {description}: {pattern}"
    
    # Check for picamera2 via requirements.txt or libcamera
    assert 'requirements.txt' in content or 'python3-libcamera' in content or \
           'libcamera' in content, "Missing camera library dependencies"
