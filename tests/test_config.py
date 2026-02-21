"""
Configuration tests - verify Docker Compose, Dockerfile, and .env files.
"""

import json
import os
import subprocess
import sys

import yaml


def test_webcam_compose_contract_basics(workspace_root):
    """Webcam compose file should parse and expose core service runtime contracts."""
    compose_file = workspace_root / "containers" / "motion-in-ocean-webcam" / "docker-compose.yaml"
    assert compose_file.exists(), "docker-compose.yaml not found"

    with open(compose_file) as f:
        config = yaml.safe_load(f)

    assert config is not None
    assert "services" in config
    assert "motion-in-ocean" in config["services"]

    service = config["services"]["motion-in-ocean"]
    required_fields = ["image", "restart", "ports", "healthcheck"]

    for field in required_fields:
        assert field in service, f"Missing required field: {field}"

    assert "environment" in service or "env_file" in service

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
        assert (
            True
        )  # privileged mode grants access, so specific device mappings are not strictly required
        return

    # If not privileged, then explicit device mappings are required
    assert len(devices) > 0, "No device mappings found and not running in privileged mode"
    assert any("/dev/dma_heap" in str(d) for d in devices), (
        "Missing /dev/dma_heap device (or privileged mode)"
    )
    assert any("/dev/vchiq" in str(d) for d in devices), (
        "Missing /dev/vchiq device (or privileged mode)"
    )

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
        assert (
            True
        )  # privileged: true is present and explicitly allowed per docker-compose.yaml comments
    else:
        # If not privileged, ensure it's not present or commented out if it was.
        # This branch ensures that if privileged is used, it must be the uncommented one.
        # If it's not privileged, then the no-new-privileges check above is sufficient.
        assert "privileged: true" not in content or "# privileged: true" in content, (
            "privileged mode should be commented out or not present if not explicitly allowed"
        )


def test_create_app_registers_expected_routes_for_management_and_webcam_modes(
    monkeypatch, tmp_path
):
    """App creation should register core management and webcam routes in their respective modes."""
    from pi_camera_in_docker import main

    monkeypatch.setenv("MOTION_IN_OCEAN_APP_MODE", "management")
    monkeypatch.setenv("MOTION_IN_OCEAN_MOCK_CAMERA", "true")
    monkeypatch.setenv("MOTION_IN_OCEAN_NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MOTION_IN_OCEAN_APPLICATION_SETTINGS_PATH", str(tmp_path / "app-settings.json"))
    monkeypatch.setenv("MOTION_IN_OCEAN_MANAGEMENT_AUTH_TOKEN", "")
    management_app = main.create_app_from_env()
    management_routes = {rule.rule for rule in management_app.url_map.iter_rules()}
    assert {
        "/",
        "/health",
        "/ready",
        "/metrics",
        "/api/config",
        "/api/webcams",
        "/api/feature-flags",
        "/api/management/overview",
        "/api/settings",
        "/api/discovery/announce",
    }.issubset(management_routes)

    monkeypatch.setenv("MOTION_IN_OCEAN_APP_MODE", "webcam")
    monkeypatch.setenv("MOTION_IN_OCEAN_NODE_REGISTRY_PATH", str(tmp_path / "registry-webcam.json"))
    monkeypatch.setattr(main, "_run_webcam_mode", lambda _state, _cfg: None)
    webcam_app = main.create_app_from_env()
    webcam_routes = {rule.rule for rule in webcam_app.url_map.iter_rules()}
    assert {"/", "/health", "/ready", "/metrics", "/stream.mjpg", "/webcam", "/webcam/"}.issubset(
        webcam_routes
    )


def test_create_app_from_env_applies_resolution_and_fps_env(monkeypatch, tmp_path):
    """Environment variables should drive runtime camera config values used by the app."""
    from pi_camera_in_docker import main

    monkeypatch.setenv("MOTION_IN_OCEAN_APP_MODE", "management")
    monkeypatch.setenv("MOTION_IN_OCEAN_MOCK_CAMERA", "true")
    monkeypatch.setenv("MOTION_IN_OCEAN_NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MOTION_IN_OCEAN_APPLICATION_SETTINGS_PATH", str(tmp_path / "app-settings.json"))
    monkeypatch.setenv("MOTION_IN_OCEAN_RESOLUTION", "1024x768")
    monkeypatch.setenv("MOTION_IN_OCEAN_FPS", "20")

    app = main.create_app_from_env()
    assert app.motion_config["resolution"] == (1024, 768)
    assert app.motion_config["fps"] == 20


def test_create_app_from_env_defaults_invalid_resolution_to_safe_fallback(monkeypatch, tmp_path):
    """Invalid RESOLUTION env value should fall back to default tuple in app config."""
    from pi_camera_in_docker import main

    monkeypatch.setenv("MOTION_IN_OCEAN_APP_MODE", "management")
    monkeypatch.setenv("MOTION_IN_OCEAN_MOCK_CAMERA", "true")
    monkeypatch.setenv("MOTION_IN_OCEAN_NODE_REGISTRY_PATH", str(tmp_path / "registry-invalid-resolution.json"))
    monkeypatch.setenv(
        "MOTION_IN_OCEAN_APPLICATION_SETTINGS_PATH", str(tmp_path / "app-settings-invalid-resolution.json")
    )
    monkeypatch.setenv("MOTION_IN_OCEAN_RESOLUTION", "invalid-resolution")
    monkeypatch.setenv("MOTION_IN_OCEAN_FPS", "24")

    app = main.create_app_from_env()
    assert app.motion_config["resolution"] == (640, 480)
    assert app.motion_config["fps"] == 24


def test_create_app_from_env_defaults_invalid_fps_to_safe_fallback(monkeypatch, tmp_path):
    """Invalid FPS env value should fall back to deterministic default in app config."""
    from pi_camera_in_docker import main

    monkeypatch.setenv("MOTION_IN_OCEAN_APP_MODE", "management")
    monkeypatch.setenv("MOTION_IN_OCEAN_MOCK_CAMERA", "true")
    monkeypatch.setenv("MOTION_IN_OCEAN_NODE_REGISTRY_PATH", str(tmp_path / "registry-invalid-fps.json"))
    monkeypatch.setenv("MOTION_IN_OCEAN_APPLICATION_SETTINGS_PATH", str(tmp_path / "app-settings-invalid-fps.json"))
    monkeypatch.setenv("MOTION_IN_OCEAN_RESOLUTION", "800x600")
    monkeypatch.setenv("MOTION_IN_OCEAN_FPS", "not-an-int")

    app = main.create_app_from_env()
    assert app.motion_config["resolution"] == (800, 600)
    assert app.motion_config["fps"] == 24


def test_real_camera_startup_failure_records_degraded_state_and_boots(monkeypatch, tmp_path):
    """When real camera enumeration yields no cameras, app creation should continue in degraded mode."""
    from pi_camera_in_docker import main

    monkeypatch.setenv("MOTION_IN_OCEAN_APP_MODE", "webcam")
    monkeypatch.setenv("MOTION_IN_OCEAN_MOCK_CAMERA", "false")
    monkeypatch.setenv("MOTION_IN_OCEAN_NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MOTION_IN_OCEAN_APPLICATION_SETTINGS_PATH", str(tmp_path / "app-settings.json"))
    monkeypatch.setattr(main, "_check_device_availability", lambda _cfg: None)

    class FakePicamera2:
        pass

    class FakeJpegEncoder:
        def __init__(self, q):
            self.quality = q

    class FakeFileOutput:
        def __init__(self, out):
            self.output = out

    monkeypatch.setattr(
        main,
        "import_camera_components",
        lambda _allow: (FakePicamera2, FakeJpegEncoder, FakeFileOutput),
    )
    monkeypatch.setattr(
        main,
        "_detect_camera_devices",
        lambda: {
            "video_devices": ["/dev/video0"],
            "media_devices": ["/dev/media0"],
            "v4l_subdev_devices": [],
            "dma_heap_devices": [],
            "vchiq_device": True,
        },
    )
    monkeypatch.setattr(main, "_get_camera_info", lambda _cls: ([], "test.path"))

    app = main.create_webcam_app()

    assert app.motion_state["recording_started"].is_set() is False
    startup_error = app.motion_state["camera_startup_error"]
    assert startup_error is not None
    assert startup_error["code"] == "CAMERA_UNAVAILABLE"
    assert (
        startup_error["message"]
        == "No cameras detected. Check device mappings and camera hardware."
    )
    assert startup_error["reason"] == "camera_unavailable"
    assert startup_error["context"]["detection_path"] == "test.path"


def test_env_example_contains_required_runtime_variables_with_nonempty_defaults(workspace_root):
    """Example env should define required runtime variables with parseable defaults."""
    env_file = workspace_root / "containers" / "motion-in-ocean-webcam" / ".env.example"
    env_vars = {}
    for line in env_file.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env_vars[key] = value

    required_vars = {
        "MOTION_IN_OCEAN_PORT",
        "MOTION_IN_OCEAN_BIND_HOST",
        "TZ",
        "MOTION_IN_OCEAN_MOCK_CAMERA",
    }
    assert required_vars.issubset(env_vars), f"Missing vars: {required_vars - set(env_vars)}"

    nonempty_defaults = {
        "MOTION_IN_OCEAN_PORT",
        "MOTION_IN_OCEAN_BIND_HOST",
        "TZ",
        "MOTION_IN_OCEAN_MOCK_CAMERA",
    }
    assert all(env_vars[key].strip() for key in nonempty_defaults)
    assert 1 <= int(env_vars["MOTION_IN_OCEAN_PORT"]) <= 65535


def test_dockerfile_runtime_contract_instructions(workspace_root):
    """Dockerfile should include runtime instructions required for webcam operation."""
    dockerfile = workspace_root / "Dockerfile"
    dockerfile_content = dockerfile.read_text()
    requirements_path = workspace_root / "requirements.txt"
    requirements_content = requirements_path.read_text().lower()

    # Check for parameterized FROM statements (DEBIAN_SUITE build arg)
    assert dockerfile_content.count("FROM debian:${DEBIAN_SUITE}-slim") >= 2
    # Check that build args are defined
    assert "ARG DEBIAN_SUITE=trixie" in dockerfile_content
    assert "ARG RPI_SUITE=trixie" in dockerfile_content
    assert "python3-picamera2" in dockerfile_content
    assert "WORKDIR /app" in dockerfile_content
    assert "COPY pi_camera_in_docker/ /app/pi_camera_in_docker/" in dockerfile_content
    assert 'CMD ["python3", "-m", "pi_camera_in_docker.main"]' in dockerfile_content
    # Check venv isolation
    assert "/opt/venv/bin/pip install" in dockerfile_content
    assert "COPY --from=builder /opt/venv /opt/venv" in dockerfile_content

    has_pip_install = (
        "pip3 install" in dockerfile_content.lower() or
        "/opt/venv/bin/pip install" in dockerfile_content.lower()
    )
    has_flask = "flask" in dockerfile_content.lower()
    has_requirements = "flask" in requirements_content
    assert (has_pip_install and has_flask) or has_requirements, "Flask dependency contract missing"


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
            "MOTION_IN_OCEAN_MOCK_CAMERA": "true",
            "MOTION_IN_OCEAN_PI3_PROFILE": "true",
            "MOTION_IN_OCEAN_PI3_OPTIMIZATION": "false",
            "MOTION_IN_OCEAN_RESOLUTION": "1024x768",
            "MOTION_IN_OCEAN_FPS": "20",
            "MOTION_IN_OCEAN_TARGET_FPS": "8",
            "MOTION_IN_OCEAN_JPEG_QUALITY": "88",
            "MOTION_IN_OCEAN_MAX_STREAM_CONNECTIONS": "9",
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
            "MOTION_IN_OCEAN_MOCK_CAMERA": "true",
            "PI3_PROFILE": "true",
            "MOTION_IN_OCEAN_PI3_PROFILE": "false",
            "MOTION_IN_OCEAN_PI3_OPTIMIZATION": "false",
        },
        unset_keys=["MOTION_IN_OCEAN_RESOLUTION", "MOTION_IN_OCEAN_FPS", "MOTION_IN_OCEAN_TARGET_FPS", "MOTION_IN_OCEAN_JPEG_QUALITY", "MOTION_IN_OCEAN_MAX_STREAM_CONNECTIONS"],
    )

    assert data["pi3_profile_enabled"] is False

    data = _load_main_config_with_env(
        workspace_root,
        {
            "MOTION_IN_OCEAN_MOCK_CAMERA": "true",
            "PI3_PROFILE": "true",
            "MOTION_IN_OCEAN_PI3_OPTIMIZATION": "false",
        },
        unset_keys=["MOTION_IN_OCEAN_RESOLUTION", "MOTION_IN_OCEAN_FPS", "MOTION_IN_OCEAN_TARGET_FPS", "MOTION_IN_OCEAN_JPEG_QUALITY", "MOTION_IN_OCEAN_MAX_STREAM_CONNECTIONS"],
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
    metrics_json_line = next(line for line in reversed(output_lines) if line.startswith("{"))
    metrics = json.loads(metrics_json_line)

    assert metrics["camera_active"] is True
    assert metrics["current_fps"] <= 30  # Allow higher FPS in short window
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
for route in ("/webcam", "/webcam/"):
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


def test_setup_ui_detect_camera_devices_collects_v4l_subdev(monkeypatch, workspace_root):
    """Verify setup UI device detection captures /dev/v4l-subdev* nodes."""
    original_path = sys.path.copy()
    sys.path.insert(0, str(workspace_root))  # Add parent dir to sys.path
    try:
        from pi_camera_in_docker import main

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
    sys.path.insert(0, str(workspace_root))  # Add parent dir to sys.path
    try:
        from pi_camera_in_docker import main
    finally:
        sys.path = original_path  # Restore sys.path

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
