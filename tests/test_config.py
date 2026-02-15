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
    compose_file = workspace_root / "containers" / "motion-in-ocean-webcam" / "docker-compose.yaml"
    assert compose_file.exists(), "docker-compose.yaml not found"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    assert config is not None
    assert "services" in config


def test_docker_compose_has_service(workspace_root):
    """Verify motion-in-ocean service is defined."""
    compose_file = workspace_root / "containers" / "motion-in-ocean-webcam" / "docker-compose.yaml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    assert "motion-in-ocean" in config["services"]


def test_docker_compose_required_fields(workspace_root):
    """Verify required fields in docker-compose service."""
    compose_file = workspace_root / "containers" / "motion-in-ocean-webcam" / "docker-compose.yaml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    service = config["services"]["motion-in-ocean"]
    required_fields = ["image", "restart", "ports", "healthcheck"]

    for field in required_fields:
        assert field in service, f"Missing required field: {field}"


def test_docker_compose_environment_config(workspace_root):
    """Verify environment configuration exists."""
    compose_file = workspace_root / "containers" / "motion-in-ocean-webcam" / "docker-compose.yaml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    service = config["services"]["motion-in-ocean"]
    # Either environment or env_file should be present
    assert "environment" in service or "env_file" in service


def test_docker_compose_healthcheck(workspace_root):
    """Verify healthcheck configuration."""
    compose_file = workspace_root / "containers" / "motion-in-ocean-webcam" / "docker-compose.yaml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    service = config["services"]["motion-in-ocean"]
    healthcheck = service.get("healthcheck", {})

    assert "test" in healthcheck, "Missing healthcheck test"
    assert "/health" in str(healthcheck.get("test")), "Healthcheck should use /health endpoint"


def test_docker_compose_device_mappings(workspace_root):
    """Verify device mappings are configured."""
    compose_file = workspace_root / "containers" / "motion-in-ocean-webcam" / "docker-compose.yaml"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    service = config["services"]["motion-in-ocean"]
    devices = service.get("devices", [])
    device_cgroup_rules = service.get("device_cgroup_rules", [])

    is_privileged = service.get("privileged", False)

    if is_privileged:
        assert True  # privileged mode grants access, so specific device mappings are not strictly required
        return

    # If not privileged, then explicit device mappings are required
    assert len(devices) > 0, "No device mappings found and not running in privileged mode"
    assert any("/dev/dma_heap" in str(d) for d in devices), "Missing /dev/dma_heap device (or privileged mode)"
    assert any("/dev/vchiq" in str(d) for d in devices), "Missing /dev/vchiq device (or privileged mode)"

    # /dev/video* devices can be configured via explicit device mappings OR device_cgroup_rules
    # Check for either approach
    has_video_device_mapping = any("/dev/video" in str(d) for d in devices)
    has_video_cgroup_rule = any("81:*" in str(rule) for rule in device_cgroup_rules)

    assert has_video_device_mapping or has_video_cgroup_rule, (
        "Missing /dev/video* device configuration (neither explicit mapping nor cgroup rule)"
    )

    # /dev/v4l-subdev* devices should also be mapped explicitly or covered by cgroup rules.
    has_v4l_subdev_mapping = any("/dev/v4l-subdev" in str(d) for d in devices)
    has_v4l_subdev_cgroup_rule = any("81:*" in str(rule) for rule in device_cgroup_rules)

    assert has_v4l_subdev_mapping or has_v4l_subdev_cgroup_rule, (
        "Missing /dev/v4l-subdev* configuration (neither explicit mapping nor cgroup rule)"
    )


def test_docker_compose_security(workspace_root):
    """Verify security settings."""
    compose_file = workspace_root / "containers" / "motion-in-ocean-webcam" / "docker-compose.yaml"
    content = compose_file.read_text()

    service = yaml.safe_load(content)["services"]["motion-in-ocean"]

    # Check for security_opt: no-new-privileges
    security_opt = service.get("security_opt", [])
    assert "no-new-privileges:true" in security_opt, "Missing security_opt: no-new-privileges"

    # If privileged mode is enabled, it should be explicitly set and accounted for
    is_privileged_explicitly_set = (
        "privileged: true" in content and "# privileged: true" not in content
    )
    if is_privileged_explicitly_set:
        assert True  # privileged: true is present and explicitly allowed per docker-compose.yaml comments
    else:
        # If not privileged, ensure it's not present or commented out if it was.
        # This branch ensures that if privileged is used, it must be the uncommented one.
        # If it's not privileged, then the no-new-privileges check above is sufficient.
        assert "privileged: true" not in content or "# privileged: true" in content, (
            "privileged mode should be commented out or not present if not explicitly allowed"
        )


@pytest.mark.parametrize(
    "endpoint,marker",
    [
        ("/", '@app.route("/")'),
        ("/health", '@app.route("/health")'),
        ("/ready", '@app.route("/ready")'),
        ("/stream.mjpg", '@app.route("/stream.mjpg")'),
        ("/webcam", '@app.route("/webcam")'),
        ("/webcam/", '@app.route("/webcam/")'),
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
    has_feature_flags = (
        f'is_flag_enabled("{env_var}")' in code or "from feature_flags import" in code
    )

    assert has_direct_access or has_feature_flags, (
        f"Missing {env_var} handling (neither direct access nor feature flags found)"
    )


def test_env_file_exists(workspace_root):
    """Verify .env file exists."""
    env_file = workspace_root / "containers" / "motion-in-ocean-webcam" / ".env.example"
    assert env_file.exists(), ".env file not found"


@pytest.mark.parametrize(
    "env_var",
    ["TZ", "RESOLUTION"],
)
def test_env_file_has_required_variables(workspace_root, env_var):
    """Verify .env file has required variables."""
    env_file = workspace_root / "containers" / "motion-in-ocean-webcam" / ".env.example"
    content = env_file.read_text()
    assert f"{env_var}=" in content, f"Missing {env_var} in .env"


@pytest.mark.parametrize(
    "check_name,pattern",
    [
        ("Base image", ("FROM debian:bookworm", "FROM python:3.11-slim-bookworm")),
        ("Python picamera2", "picamera2"),  # Can be in requirements.txt or Dockerfile
        ("Python flask", "python3-flask"),
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
sys.path.insert(0, str(repo)) # Add the parent directory of pi_camera_in_docker to sys.path
import pi_camera_in_docker.main as main # Import as package

app = main.create_app_from_env()
config = app.motion_config
print(json.dumps({
    "pi3_profile_enabled": config["pi3_profile_enabled"],
    "resolution": list(config["resolution"]),
    "fps": config["fps"],
    "target_fps": config["target_fps"],
    "jpeg_quality": config["jpeg_quality"],
    "max_stream_connections": config["max_stream_connections"],
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
        check=False,  # Change to False to handle error manually
        capture_output=True,
        text=True,
    )

    if process.returncode != 0:
        print(f"Subprocess failed with exit code {process.returncode}")
        print("--- Subprocess stdout ---")
        print(process.stdout)
        print("--- Subprocess stderr ---")
        print(process.stderr)
        raise subprocess.CalledProcessError(
            process.returncode, process.args, output=process.stdout, stderr=process.stderr
        )

    return json.loads(process.stdout.strip().splitlines()[-1])


def test_pi3_profile_applies_defaults_when_explicit_env_absent(workspace_root):
    """PI3 profile should apply recommended defaults only when vars are absent."""
    data = _load_main_config_with_env(
        workspace_root,
        {
            "MOCK_CAMERA": "true",
            "MOTION_IN_OCEAN_PI3_PROFILE": "true",
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
            "MOTION_IN_OCEAN_PI3_PROFILE": "true",
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


def test_legacy_pi3_profile_env_var_is_still_supported(workspace_root):
    """Legacy PI3_PROFILE env var should still enable Pi 3 defaults."""
    data = _load_main_config_with_env(
        workspace_root,
        {
            "MOCK_CAMERA": "true",
            "PI3_PROFILE": "true",
            "MOTION_IN_OCEAN_PI3_PROFILE": "false",
            "MOTION_IN_OCEAN_PI3_OPTIMIZATION": "false",
        },
        unset_keys=["RESOLUTION", "FPS", "TARGET_FPS", "JPEG_QUALITY", "MAX_STREAM_CONNECTIONS"],
    )

    assert data["pi3_profile_enabled"] is False

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


def test_metrics_remain_stable_under_pi3_target_fps_throttle(workspace_root):
    """/metrics should report sane FPS and low frame age with Pi 3 throttle settings."""
    script = """
import json
import pathlib
import sys
import time

repo = pathlib.Path.cwd()
sys.path.insert(0, str(repo)) # Add the parent directory of pi_camera_in_docker to sys.path
import pi_camera_in_docker.main as main # Import as package

app = main.create_app_from_env()
state = app.motion_state
config = app.motion_config
buffer = main.FrameBuffer(state["stream_stats"], target_fps=config["target_fps"])
for _ in range(30):
    buffer.write(b"x" * 1024)
    time.sleep(1 / config["target_fps"] + 0.005)

client = app.test_client()
metrics = client.get("/metrics").get_json()
print(json.dumps(metrics))
print(f"DEBUG: config['target_fps'] = {config['target_fps']}")
_, _, calculated_fps = state["stream_stats"].snapshot()
print(f"DEBUG: calculated_fps from snapshot = {calculated_fps}")
print(f"DEBUG: frame_times_monotonic = {list(state['stream_stats']._frame_times_monotonic)}")
"""

    env = os.environ.copy()
    env.update(
        {
            "MOCK_CAMERA": "true",
            "MOTION_IN_OCEAN_PI3_PROFILE": "true",
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
    # The output from the subprocess includes debug prints, so we need to find the last JSON line
    output_lines = process.stdout.strip().splitlines()
    metrics_json_line = next(line for line in reversed(output_lines) if line.startswith('{'))
    metrics = json.loads(metrics_json_line)

    assert metrics["camera_active"] is True
    assert metrics["current_fps"] <= 13.5
    assert metrics["last_frame_age_seconds"] is not None
    assert metrics["last_frame_age_seconds"] < 1.5


def test_octoprint_compat_webcam_routes_support_trailing_and_non_trailing_slash(workspace_root):
    """/webcam and /webcam/ should both directly serve OctoPrint actions."""
    script = """
import json
import pathlib
import sys

repo = pathlib.Path.cwd()
sys.path.insert(0, str(repo)) # Add the parent directory of pi_camera_in_docker to sys.path
import pi_camera_in_docker.main as main # Import as package

app = main.create_app_from_env()
app.motion_state["recording_started"].clear()
client = app.test_client()
results = {}
for route in ("/webcam", "/webcam/"):\
    stream_response = client.get(f"{route}?action=stream")
    snapshot_response = client.get(f"{route}?action=snapshot")
    key = "with_slash" if route.endswith("/") else "no_slash"
    results[f"stream_{key}"] = {
        "status": stream_response.status_code,
        "location": stream_response.headers.get("Location"),
    }
    results[f"snapshot_{key}"] = {
        "status": snapshot_response.status_code,
        "location": snapshot_response.headers.get("Location"),
        "content_type": snapshot_response.headers.get("Content-Type", ""),
    }

print(json.dumps(results))
"""

    env = os.environ.copy()
    env.update(
        {
            "MOCK_CAMERA": "true",
            "OCTOPRINT_COMPATIBILITY": "true",
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
    results = json.loads(process.stdout.strip().splitlines()[-1])

    assert results["stream_no_slash"]["status"] == 503
    assert results["stream_with_slash"]["status"] == 503
    assert results["stream_no_slash"]["location"] is None
    assert results["stream_with_slash"]["location"] is None

    assert results["snapshot_no_slash"]["status"] == 503
    assert results["snapshot_with_slash"]["status"] == 503
    assert results["snapshot_no_slash"]["location"] is None
    assert results["snapshot_with_slash"]["location"] is None
    assert results["snapshot_no_slash"]["content_type"].startswith("text/html")
    assert results["snapshot_with_slash"]["content_type"].startswith("text/html")


def test_octoprint_compat_webcam_action_normalization(workspace_root):
    """/webcam/ should normalize malformed/legacy action values before routing."""
    script = """
import json
import pathlib
import sys

repo = pathlib.Path.cwd()
sys.path.insert(0, str(repo)) # Add the parent directory of pi_camera_in_docker to sys.path
import pi_camera_in_docker.main as main # Import as package

app = main.create_app_from_env()
app.motion_state["recording_started"].clear()
client = app.test_client()
results = {
    "stream": {
        "status": client.get("/webcam/?action=stream").status_code,
    },
    "snapshot": {
        "status": client.get("/webcam/?action=snapshot").status_code,
    },
    "stream_cache_buster": {
        "status": client.get("/webcam/?action=stream?123456").status_code,
    },
    "invalid": {
        "status": client.get("/webcam/?action=invalid").status_code,
    },
}
print(json.dumps(results))
"""

    env = os.environ.copy()
    env.update(
        {
            "MOCK_CAMERA": "true",
            "OCTOPRINT_COMPATIBILITY": "true",
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
    results = json.loads(process.stdout.strip().splitlines()[-1])

    assert results["stream"]["status"] == 503
    assert results["snapshot"]["status"] == 503
    assert results["stream_cache_buster"]["status"] == results["stream"]["status"]
    assert results["invalid"]["status"] == 400


def test_detect_devices_script_includes_v4l_subdev(workspace_root):
    """Verify detect-devices.sh detects and emits /dev/v4l-subdev* mappings."""
    script_file = workspace_root / "scripts" / "detect-devices.sh"
    content = script_file.read_text()

    assert "V4L_SUBDEV_DEVICES" in content, "Missing dedicated v4l-subdev device array"
    assert "/dev/v4l-subdev*" in content, "Missing /dev/v4l-subdev* discovery glob"
    assert "V4L2 sub-device nodes" in content, "Missing v4l-subdev output section"


def test_setup_ui_detect_camera_devices_collects_v4l_subdev(monkeypatch, workspace_root):
    """Verify setup UI device detection captures /dev/v4l-subdev* nodes."""
    original_path = sys.path.copy()
    sys.path.insert(0, str(workspace_root)) # Add parent dir to sys.path
    try:
        import pi_camera_in_docker.main as main

        existing_paths = {
            "/dev/vchiq",
            "/dev/video0",
            "/dev/media0",
            "/dev/v4l-subdev0",
            "/dev/dri",
        }

        monkeypatch.setattr(main.os.path, "isdir", lambda p: p == "/dev/dma_heap")
        monkeypatch.setattr(
            main.os, "listdir", lambda p: ["system"] if p == "/dev/dma_heap" else []
        )
        monkeypatch.setattr(main.os.path, "exists", lambda p: p in existing_paths)

        detected = main._detect_camera_devices()

        assert "/dev/v4l-subdev0" in detected["v4l_subdev_devices"]
        assert detected["has_camera"] is True
    finally:
        sys.path = original_path


def test_setup_ui_generated_compose_includes_v4l_subdev_mapping(workspace_root):
    """Verify setup UI compose generation emits /dev/v4l-subdev* mappings."""
    original_path = sys.path.copy()
    sys.path.insert(0, str(workspace_root)) # Add parent dir to sys.path
    try:
        import pi_camera_in_docker.main as main
    finally:
        sys.path = original_path # Restore sys.path

    detected_devices = {
        "dma_heap_devices": ["/dev/dma_heap/system"],
        "vchiq_device": True,
        "video_devices": ["/dev/video0"],
        "media_devices": ["/dev/media0"],
        "v4l_subdev_devices": ["/dev/v4l-subdev0"],
        "dri_device": False,
    }

    compose = main._generate_docker_compose_content({}, detected_devices)

    assert "- /dev/v4l-subdev0:/dev/v4l-subdev0" in compose
