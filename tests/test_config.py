"""
Configuration tests - verify Docker Compose, Dockerfile, and .env files.
"""

import ast
import json
import os
import subprocess
import sys

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
    """Test if docker-compose.yaml is valid YAML."""
    compose_file = workspace_root / "docker-compose.yaml"
    assert compose_file.exists(), "docker-compose.yaml not found"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    assert config is not None
    assert "services" in config


def test_docker_compose_has_service(workspace_root):
    """Verify motion-in-ocean service is defined."""
    compose_file = workspace_root / "docker-compose.yaml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    assert "motion-in-ocean" in config["services"]


def test_docker_compose_required_fields(workspace_root):
    """Verify required fields in docker-compose service."""
    compose_file = workspace_root / "docker-compose.yaml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    service = config["services"]["motion-in-ocean"]
    required_fields = ["image", "restart", "ports", "healthcheck"]

    for field in required_fields:
        assert field in service, f"Missing required field: {field}"


def test_docker_compose_environment_config(workspace_root):
    """Verify environment configuration exists."""
    compose_file = workspace_root / "docker-compose.yaml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    service = config["services"]["motion-in-ocean"]
    # Either environment or env_file should be present
    assert "environment" in service or "env_file" in service


def test_docker_compose_healthcheck(workspace_root):
    """Verify healthcheck configuration."""
    compose_file = workspace_root / "docker-compose.yaml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    service = config["services"]["motion-in-ocean"]
    healthcheck = service.get("healthcheck", {})

    assert "test" in healthcheck, "Missing healthcheck test"
    assert "/health" in str(healthcheck.get("test")), "Healthcheck should use /health endpoint"


def test_docker_compose_device_mappings(workspace_root):
    """Verify device mappings are configured."""
    compose_file = workspace_root / "docker-compose.yaml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    service = config["services"]["motion-in-ocean"]
    devices = service.get("devices", [])
    device_cgroup_rules = service.get("device_cgroup_rules", [])

    assert len(devices) > 0, "No device mappings found"
    assert any("/dev/dma_heap" in str(d) for d in devices), "Missing /dev/dma_heap device"
    assert any("/dev/vchiq" in str(d) for d in devices), "Missing /dev/vchiq device"

    # /dev/video* devices can be configured via explicit device mappings OR device_cgroup_rules
    # Check for either approach
    has_video_device_mapping = any("/dev/video" in str(d) for d in devices)
    has_video_cgroup_rule = any("81:*" in str(rule) for rule in device_cgroup_rules)

    assert has_video_device_mapping or has_video_cgroup_rule, (
        "Missing /dev/video* device configuration (neither explicit mapping nor cgroup rule)"
    )


def test_docker_compose_security(workspace_root):
    """Verify security settings."""
    compose_file = workspace_root / "docker-compose.yaml"
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
    ["RESOLUTION", "FPS"],
)
def test_environment_variable_handled(workspace_root, env_var):
    """Verify environment variables are handled in main.py.
    
    Tests that env vars are handled either directly via os.environ.get()
    or through the feature flags system (which supports backward compatibility).
    """
    main_py = workspace_root / "pi_camera_in_docker" / "main.py"
    code = main_py.read_text()
    
    # Check for direct env var handling OR feature flags system (backward compat)
    has_direct_access = f'os.environ.get("{env_var}"' in code
    has_feature_flags = f'is_flag_enabled("{env_var}")' in code or "from feature_flags import" in code
    
    assert (
        has_direct_access or has_feature_flags
    ), f"Missing {env_var} handling (neither direct access nor feature flags found)"


def test_env_file_exists(workspace_root):
    """Verify .env file exists."""
    env_file = workspace_root / ".env"
    assert env_file.exists(), ".env file not found"


@pytest.mark.parametrize(
    "env_var",
    ["TZ", "RESOLUTION"],
)
def test_env_file_has_required_variables(workspace_root, env_var):
    """Verify .env file has required variables."""
    env_file = workspace_root / ".env"
    content = env_file.read_text()
    assert f"{env_var}=" in content, f"Missing {env_var} in .env"


@pytest.mark.parametrize(
    "check_name,pattern",
    [
        ("Base image", ("FROM debian:bookworm", "FROM python:3.11-slim-bookworm")),
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
    if isinstance(pattern, tuple):
        assert any(item in combined_content for item in pattern), (
            "Missing in Dockerfile/requirements.txt: " + check_name
        )
        return

    assert pattern in combined_content, f"Missing in Dockerfile/requirements.txt: {check_name}"


def _load_main_config_with_env(workspace_root, env_updates, unset_keys=None):
    """Load main.py in a clean subprocess and return selected config values."""
    script = """
import json
import pathlib
import sys

repo = pathlib.Path.cwd()
sys.path.insert(0, str(repo / "pi_camera_in_docker"))
import main

print(json.dumps({
    "pi3_profile_enabled": main.pi3_profile_enabled,
    "resolution": list(main.resolution),
    "fps": main.fps,
    "target_fps": main.target_fps,
    "jpeg_quality": main.jpeg_quality,
    "max_stream_connections": main.max_stream_connections,
}))
"""
    env = os.environ.copy()
    for key in unset_keys or []:
        env.pop(key, None)
    env.update(env_updates)
    process = subprocess.run(
        [sys.executable, "-c", script],
        cwd=workspace_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(process.stdout.strip().splitlines()[-1])


def test_pi3_profile_applies_defaults_when_explicit_env_absent(workspace_root):
    """PI3 profile should apply recommended defaults only when vars are absent."""
    data = _load_main_config_with_env(
        workspace_root,
        {
            "MOCK_CAMERA": "true",
            "PI3_PROFILE": "true",
            "MOTION_IN_OCEAN_PI3_OPTIMIZATION": "false",
        },
        unset_keys=["RESOLUTION", "FPS", "TARGET_FPS", "JPEG_QUALITY", "MAX_STREAM_CONNECTIONS"],
    )

    assert data["pi3_profile_enabled"] is True
    assert data["resolution"] == [640, 480]
    assert data["fps"] == 12
    assert data["target_fps"] == 12
    assert data["jpeg_quality"] == 75
    assert data["max_stream_connections"] == 3


def test_manual_env_values_override_pi3_profile_defaults(workspace_root):
    """Manual env values should take precedence over PI3 profile defaults."""
    data = _load_main_config_with_env(
        workspace_root,
        {
            "MOCK_CAMERA": "true",
            "PI3_PROFILE": "true",
            "MOTION_IN_OCEAN_PI3_OPTIMIZATION": "false",
            "RESOLUTION": "1024x768",
            "FPS": "20",
            "TARGET_FPS": "8",
            "JPEG_QUALITY": "88",
            "MAX_STREAM_CONNECTIONS": "9",
        },
    )

    assert data["pi3_profile_enabled"] is True
    assert data["resolution"] == [1024, 768]
    assert data["fps"] == 20
    assert data["target_fps"] == 8
    assert data["jpeg_quality"] == 88
    assert data["max_stream_connections"] == 9


def test_metrics_remain_stable_under_pi3_target_fps_throttle(workspace_root):
    """/metrics should report sane FPS and low frame age with Pi 3 throttle settings."""
    script = """
import json
import pathlib
import sys
import time

repo = pathlib.Path.cwd()
sys.path.insert(0, str(repo / "pi_camera_in_docker"))
import main

buffer = main.FrameBuffer(main.stream_stats, target_fps=main.target_fps)
for _ in range(30):
    buffer.write(b"x" * 1024)
    time.sleep(0.01)

client = main.app.test_client()
metrics = client.get("/metrics").get_json()
print(json.dumps(metrics))
"""

    env = os.environ.copy()
    env.update(
        {
            "MOCK_CAMERA": "true",
            "PI3_PROFILE": "true",
            "MOTION_IN_OCEAN_PI3_OPTIMIZATION": "false",
            "TARGET_FPS": "12",
        }
    )

    process = subprocess.run(
        [sys.executable, "-c", script],
        cwd=workspace_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    metrics = json.loads(process.stdout.strip().splitlines()[-1])

    assert metrics["camera_active"] is False
    assert metrics["current_fps"] <= 13.5
    assert metrics["last_frame_age_seconds"] is not None
    assert metrics["last_frame_age_seconds"] < 1.5
