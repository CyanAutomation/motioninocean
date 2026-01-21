"""
Configuration tests - verify Docker Compose, Dockerfile, and .env files.
"""

import ast
from pathlib import Path

import pytest
import yaml


def test_python_syntax(workspace_root):
    """Test if main.py has valid Python syntax."""
    main_py = workspace_root / "pi_camera_in_docker" / "main.py"
    assert main_py.exists(), "main.py not found"

    code = main_py.read_text()
    # This will raise SyntaxError if invalid
    ast.parse(code)


def test_docker_compose_valid_yaml(workspace_root):
    """Test if docker-compose.yml is valid YAML."""
    compose_file = workspace_root / "docker-compose.yml"
    assert compose_file.exists(), "docker-compose.yml not found"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    assert config is not None
    assert "services" in config


def test_docker_compose_has_service(workspace_root):
    """Verify motion-in-ocean service is defined."""
    compose_file = workspace_root / "docker-compose.yml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    assert "motion-in-ocean" in config["services"]


def test_docker_compose_required_fields(workspace_root):
    """Verify required fields in docker-compose service."""
    compose_file = workspace_root / "docker-compose.yml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    service = config["services"]["motion-in-ocean"]
    required_fields = ["image", "restart", "ports", "healthcheck"]

    for field in required_fields:
        assert field in service, f"Missing required field: {field}"


def test_docker_compose_environment_config(workspace_root):
    """Verify environment configuration exists."""
    compose_file = workspace_root / "docker-compose.yml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    service = config["services"]["motion-in-ocean"]
    # Either environment or env_file should be present
    assert "environment" in service or "env_file" in service


def test_docker_compose_healthcheck(workspace_root):
    """Verify healthcheck configuration."""
    compose_file = workspace_root / "docker-compose.yml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    service = config["services"]["motion-in-ocean"]
    healthcheck = service.get("healthcheck", {})

    assert "test" in healthcheck, "Missing healthcheck test"
    assert "/health" in str(healthcheck.get("test")), "Healthcheck should use /health endpoint"


def test_docker_compose_device_mappings(workspace_root):
    """Verify device mappings are configured."""
    compose_file = workspace_root / "docker-compose.yml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    service = config["services"]["motion-in-ocean"]
    devices = service.get("devices", [])

    assert len(devices) > 0, "No device mappings found"
    assert any("/dev/dma_heap" in str(d) for d in devices), "Missing /dev/dma_heap device"
    assert any("/dev/vchiq" in str(d) for d in devices), "Missing /dev/vchiq device"
    assert any("/dev/video" in str(d) for d in devices), "Missing /dev/video* devices"


def test_docker_compose_security(workspace_root):
    """Verify security settings."""
    compose_file = workspace_root / "docker-compose.yml"
    content = compose_file.read_text()

    # Privileged mode should be commented out or not present
    if "privileged: true" in content:
        assert "# privileged: true" in content, "privileged mode should be commented"


@pytest.mark.parametrize(
    "endpoint,marker",
    [
        ("/", '@app.route("/")'),
        ("/health", '@app.route("/health")'),
        ("/ready", '@app.route("/ready")'),
        ("/stream.mjpg", '@app.route("/stream.mjpg")'),
    ],
)
def test_flask_endpoint_defined(workspace_root, endpoint, marker):
    """Verify Flask endpoints are defined in main.py."""
    main_py = workspace_root / "pi_camera_in_docker" / "main.py"
    code = main_py.read_text()
    assert marker in code, f"Missing endpoint: {endpoint}"


@pytest.mark.parametrize(
    "error_type,marker",
    [
        ("PermissionError", "except PermissionError"),
        ("RuntimeError", "except RuntimeError"),
        ("General exception", "except Exception"),
        ("Try-finally", "finally:"),
    ],
)
def test_error_handling_present(workspace_root, error_type, marker):
    """Verify error handling is present in main.py."""
    main_py = workspace_root / "pi_camera_in_docker" / "main.py"
    code = main_py.read_text()
    assert marker in code, f"Missing {error_type} handling"


@pytest.mark.parametrize(
    "env_var",
    ["RESOLUTION", "EDGE_DETECTION", "FPS"],
)
def test_environment_variable_handled(workspace_root, env_var):
    """Verify environment variables are handled in main.py."""
    main_py = workspace_root / "pi_camera_in_docker" / "main.py"
    code = main_py.read_text()
    assert f'os.environ.get("{env_var}"' in code, f"Missing {env_var} handling"


def test_env_file_exists(workspace_root):
    """Verify .env file exists."""
    env_file = workspace_root / ".env"
    assert env_file.exists(), ".env file not found"


@pytest.mark.parametrize(
    "env_var",
    ["TZ", "RESOLUTION", "EDGE_DETECTION"],
)
def test_env_file_has_required_variables(workspace_root, env_var):
    """Verify .env file has required variables."""
    env_file = workspace_root / ".env"
    content = env_file.read_text()
    assert f"{env_var}=" in content, f"Missing {env_var} in .env"


@pytest.mark.parametrize(
    "check_name,pattern",
    [
        ("Base image", "FROM debian:bookworm"),
        ("Python picamera2", "picamera2"),  # Can be in requirements.txt or Dockerfile
        ("Python flask", "python3-flask"),
        ("Python opencv", "python3-opencv"),
        ("Working directory", "WORKDIR /app"),
        ("Entry point", "CMD"),
    ],
)
def test_dockerfile_has_required_elements(workspace_root, check_name, pattern):
    """Verify Dockerfile or requirements.txt has required elements."""
    dockerfile = workspace_root / "Dockerfile"
    requirements = workspace_root / "requirements.txt"
    
    dockerfile_content = dockerfile.read_text()
    requirements_content = requirements.read_text() if requirements.exists() else ""
    
    combined_content = dockerfile_content + "\n" + requirements_content
    assert pattern in combined_content, f"Missing in Dockerfile/requirements.txt: {check_name}"
