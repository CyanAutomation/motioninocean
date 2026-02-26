import pytest

from pi_camera_in_docker import runtime_config


def test_get_effective_settings_payload_uses_single_persisted_snapshot(monkeypatch):
    env_config = {
        "app_mode": "management",
        "resolution": (640, 480),
        "fps": 5,
        "target_fps": 5,
        "jpeg_quality": 90,
        "max_frame_age_seconds": 10.0,
        "max_stream_connections": 10,
        "api_test_mode_enabled": False,
        "api_test_cycle_interval_seconds": 5.0,
        "discovery_enabled": False,
        "discovery_management_url": "http://127.0.0.1:8001",
        "discovery_token": "",
        "discovery_interval_seconds": 30.0,
        "discovery_webcam_id": "",
        "log_level": "INFO",
        "log_format": "text",
        "log_include_identifiers": False,
        "cors_enabled": False,
        "cors_origins": "disabled",
        "bind_host": "127.0.0.1",
        "bind_port": 8000,
        "pi3_profile_enabled": False,
        "mock_camera": False,
        "pykms_mock_fallback_enabled": False,
        "node_registry_path": "/data/node-registry.json",
        "application_settings_path": "/data/application-settings.json",
        "management_auth_token": "",
        "webcam_control_plane_auth_token": "",
    }

    monkeypatch.setattr(runtime_config, "load_env_config", lambda: env_config)
    monkeypatch.setattr(
        runtime_config,
        "is_flag_enabled",
        lambda flag_name: {"MOCK_CAMERA": False}[flag_name],
    )

    snapshot = {
        "settings": {
            "camera": {"fps": 42},
            "feature_flags": {"MOCK_CAMERA": False},
            "logging": {},
            "discovery": {},
        },
        "last_modified": "2026-01-01T00:00:00+00:00",
        "modified_by": "api_patch",
    }

    class FlakySettingsStore:
        def __init__(self):
            self.load_calls = 0

        def load(self):
            self.load_calls += 1
            if self.load_calls == 1:
                return snapshot
            return {
                "settings": {
                    "camera": {"fps": 7},
                    "feature_flags": {"MOCK_CAMERA": True},
                    "logging": {},
                    "discovery": {},
                },
                "last_modified": "2099-01-01T00:00:00+00:00",
                "modified_by": "api_reset",
            }

    settings_store = FlakySettingsStore()

    payload = runtime_config.get_effective_settings_payload(settings_store)

    assert settings_store.load_calls == 1
    assert payload["settings"]["camera"]["fps"] == 42
    assert payload["settings"]["feature_flags"] == {"MOCK_CAMERA": False}
    assert payload["last_modified"] == "2026-01-01T00:00:00+00:00"
    assert payload["modified_by"] == "api_patch"


def test_load_env_config_supports_application_settings_path(monkeypatch):
    """APPLICATION_SETTINGS_PATH should be exposed in runtime configuration."""
    monkeypatch.setenv("MIO_APPLICATION_SETTINGS_PATH", "/tmp/custom-settings.json")

    cfg = runtime_config.load_env_config()

    assert cfg["application_settings_path"] == "/tmp/custom-settings.json"


def test_merge_config_with_persisted_settings_invalid_fps_range_falls_back(caplog):
    """Out-of-range persisted fps should keep env fps and log a warning."""
    env_config = {
        "fps": 24,
        "target_fps": 24,
        "jpeg_quality": 90,
        "discovery_interval_seconds": 30.0,
        "discovery_management_url": "http://127.0.0.1:8001",
    }
    persisted = {
        "settings": {
            "camera": {"fps": 121},
            "discovery": {},
            "logging": {},
        }
    }

    with caplog.at_level("WARNING"):
        merged = runtime_config.merge_config_with_persisted_settings(env_config, persisted)

    assert merged["fps"] == 24
    assert merged["target_fps"] == 24
    assert "Invalid persisted fps range" in caplog.text


def test_merge_config_with_persisted_settings_invalid_negative_fps_range_falls_back(caplog):
    """Negative persisted fps should keep env fps and log a warning."""
    env_config = {
        "fps": 24,
        "target_fps": 24,
        "jpeg_quality": 90,
        "discovery_interval_seconds": 30.0,
        "discovery_management_url": "http://127.0.0.1:8001",
    }
    persisted = {
        "settings": {
            "camera": {"fps": -1},
            "discovery": {},
            "logging": {},
        }
    }

    with caplog.at_level("WARNING"):
        merged = runtime_config.merge_config_with_persisted_settings(env_config, persisted)

    assert merged["fps"] == 24
    assert merged["target_fps"] == 24
    assert "Invalid persisted fps range" in caplog.text


def test_merge_config_with_persisted_settings_invalid_camera_jpeg_quality_type_falls_back(caplog):
    """Malformed persisted jpeg quality should not break merge and should keep env value."""
    env_config = {
        "jpeg_quality": 90,
        "fps": 24,
        "target_fps": 24,
        "discovery_interval_seconds": 30.0,
        "discovery_management_url": "http://127.0.0.1:8001",
    }
    persisted = {
        "settings": {
            "camera": {"jpeg_quality": "very-high"},
            "discovery": {},
            "logging": {},
        }
    }

    with caplog.at_level("WARNING"):
        merged = runtime_config.merge_config_with_persisted_settings(env_config, persisted)

    assert merged["jpeg_quality"] == 90
    assert "Invalid persisted jpeg_quality type" in caplog.text


def test_merge_config_with_persisted_settings_invalid_discovery_interval_type_falls_back(caplog):
    """Malformed persisted discovery interval should keep env value without exception."""
    env_config = {
        "jpeg_quality": 90,
        "fps": 24,
        "target_fps": 24,
        "discovery_interval_seconds": 30.0,
        "discovery_management_url": "http://127.0.0.1:8001",
    }
    persisted = {
        "settings": {
            "camera": {},
            "discovery": {"discovery_interval_seconds": {"seconds": 5}},
            "logging": {},
        }
    }

    with caplog.at_level("WARNING"):
        merged = runtime_config.merge_config_with_persisted_settings(env_config, persisted)

    assert merged["discovery_interval_seconds"] == 30.0
    assert "Invalid persisted discovery_interval_seconds type" in caplog.text


def test_merge_config_with_persisted_settings_invalid_discovery_url_type_falls_back(caplog):
    """Malformed persisted discovery URL should keep env value without exception."""
    env_config = {
        "jpeg_quality": 90,
        "fps": 24,
        "target_fps": 24,
        "discovery_interval_seconds": 30.0,
        "discovery_management_url": "http://127.0.0.1:8001",
    }
    persisted = {
        "settings": {
            "camera": {},
            "discovery": {"discovery_management_url": ["http://invalid"]},
            "logging": {},
        }
    }

    with caplog.at_level("WARNING"):
        merged = runtime_config.merge_config_with_persisted_settings(env_config, persisted)

    assert merged["discovery_management_url"] == "http://127.0.0.1:8001"
    assert "Invalid persisted discovery_management_url type" in caplog.text


def test_load_env_config_supports_webcam_control_plane_auth_token(monkeypatch):
    """WEBCAM_CONTROL_PLANE_AUTH_TOKEN should be exposed in runtime configuration."""
    monkeypatch.setenv("MIO_WEBCAM_CONTROL_PLANE_AUTH_TOKEN", "webcam-token")

    cfg = runtime_config.load_env_config()

    assert cfg["webcam_control_plane_auth_token"] == "webcam-token"


def test_merge_config_with_settings_uses_application_settings_path(monkeypatch, tmp_path):
    """merge_config_with_settings should construct ApplicationSettings from env-configured path."""
    settings_path = tmp_path / "custom-settings.json"
    env_config = {
        "application_settings_path": str(settings_path),
        "fps": 20,
    }
    observed = {"path": None}

    class StubSettingsStore:
        def __init__(self, path: str):
            observed["path"] = path

        def load(self):
            return {"settings": {"camera": {}, "discovery": {}, "logging": {}}}

    monkeypatch.setattr(runtime_config, "ApplicationSettings", StubSettingsStore)

    runtime_config.merge_config_with_settings(env_config)

    assert observed["path"] == str(settings_path)


def test_create_app_from_env_honors_application_settings_path(monkeypatch, tmp_path):
    """Application should use APPLICATION_SETTINGS_PATH for its settings persistence store."""
    from pi_camera_in_docker import main

    settings_path = tmp_path / "custom" / "app-settings.json"
    monkeypatch.setenv("MIO_APP_MODE", "management")
    monkeypatch.setenv("MIO_MOCK_CAMERA", "true")
    monkeypatch.setenv("MIO_NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MIO_APPLICATION_SETTINGS_PATH", str(settings_path))

    app = main.create_app_from_env()

    assert str(app.application_settings.path) == str(settings_path)


def test_merge_config_with_settings_logs_actionable_permission_warning(caplog):
    """Warning should preserve actionable guidance from settings permission errors."""

    class DeniedSettingsStore:
        def load(self):
            message = (
                "Permission denied while writing settings file at '/data/application-settings.json'. "
                "Check /data mount ownership and write permissions for the container user, "
                "or set APPLICATION_SETTINGS_PATH to a writable location "
                "(for example, ./data/application-settings.json)."
            )
            raise runtime_config.SettingsValidationError(message)

    env_config = {"application_settings_path": "/data/application-settings.json", "fps": 24}

    with caplog.at_level("WARNING"):
        merged = runtime_config.merge_config_with_settings(env_config, DeniedSettingsStore())

    assert merged == env_config
    assert "Could not load persisted settings:" in caplog.text
    assert "Check /data mount ownership" in caplog.text
    assert "APPLICATION_SETTINGS_PATH" in caplog.text


def test_load_networking_config_disables_cors_when_origins_unset(monkeypatch):
    """Unset CORS origins should disable CORS."""
    monkeypatch.delenv("MIO_CORS_ORIGINS", raising=False)
    monkeypatch.delenv("MIO_CORS_SUPPORT", raising=False)

    cfg = runtime_config._load_networking_config()

    assert cfg["cors_enabled"] is False
    assert cfg["cors_origins"] == "disabled"


def test_load_networking_config_enables_wildcard_cors(monkeypatch):
    """Wildcard CORS origins should enable CORS for all origins."""
    monkeypatch.setenv("MIO_CORS_ORIGINS", "*")

    cfg = runtime_config._load_networking_config()

    assert cfg["cors_enabled"] is True
    assert cfg["cors_origins"] == "*"


def test_load_networking_config_uses_configured_origins_csv(monkeypatch):
    """Comma-separated origins should be preserved for CORS configuration."""
    monkeypatch.setenv("MIO_CORS_ORIGINS", "https://example.com, https://foo.test")

    cfg = runtime_config._load_networking_config()

    assert cfg["cors_enabled"] is True
    assert cfg["cors_origins"] == "https://example.com, https://foo.test"


def test_load_networking_config_default_base_url_uses_parsed_bind_port(monkeypatch):
    """Default base URL should reuse validated bind_port when MIO_BASE_URL is unset."""
    monkeypatch.delenv("MIO_BASE_URL", raising=False)
    monkeypatch.setenv("MIO_PORT", "9000")
    monkeypatch.setattr(runtime_config.socket, "gethostname", lambda: "test-host")

    cfg = runtime_config._load_networking_config()

    assert cfg["bind_port"] == 9000
    assert cfg["base_url"] == "http://test-host:9000"


def test_load_networking_config_default_base_url_keeps_legacy_default_port(monkeypatch):
    """Unset MIO_PORT should retain the existing base URL default of :8000."""
    monkeypatch.delenv("MIO_BASE_URL", raising=False)
    monkeypatch.delenv("MIO_PORT", raising=False)
    monkeypatch.setattr(runtime_config.socket, "gethostname", lambda: "test-host")

    cfg = runtime_config._load_networking_config()

    assert cfg["bind_port"] == 8000
    assert cfg["base_url"] == "http://test-host:8000"


def test_load_networking_config_ignores_removed_cors_support_alias(monkeypatch, caplog):
    """Removed MIO_CORS_SUPPORT should not affect CORS behavior and should warn."""
    monkeypatch.delenv("MIO_CORS_ORIGINS", raising=False)
    monkeypatch.setenv("MIO_CORS_SUPPORT", "true")

    with caplog.at_level("WARNING"):
        cfg = runtime_config._load_networking_config()

    assert cfg["cors_enabled"] is False
    assert cfg["cors_origins"] == "disabled"
    assert "MIO_CORS_SUPPORT has been removed and is ignored" in caplog.text


def test_load_networking_config_keeps_origins_when_removed_cors_support_present(
    monkeypatch, caplog
):
    """MIO_CORS_ORIGINS should fully determine behavior even if removed alias is set."""
    monkeypatch.setenv("MIO_CORS_ORIGINS", "https://example.com")
    monkeypatch.setenv("MIO_CORS_SUPPORT", "false")

    with caplog.at_level("WARNING"):
        cfg = runtime_config._load_networking_config()

    assert cfg["cors_enabled"] is True
    assert cfg["cors_origins"] == "https://example.com"
    assert "MIO_CORS_SUPPORT has been removed and is ignored" in caplog.text


def test_camera_fps_default_matches_settings_schema(monkeypatch):
    """Runtime FPS fallback should match camera.fps schema default."""
    from pi_camera_in_docker.settings_schema import SettingsSchema

    monkeypatch.delenv("FPS", raising=False)

    camera_config = runtime_config._load_camera_config()
    schema_default = SettingsSchema.get_defaults()["camera"]["fps"]

    assert camera_config["fps"] == schema_default
    assert camera_config["target_fps"] == schema_default


def test_settings_api_env_defaults_use_runtime_fps_default(monkeypatch):
    """API env-default payload should expose the same FPS default as runtime config."""
    from pi_camera_in_docker.settings_api import _load_env_settings_defaults

    monkeypatch.delenv("FPS", raising=False)

    runtime_default = runtime_config._load_camera_config()["fps"]
    env_defaults = _load_env_settings_defaults()

    assert env_defaults["camera"]["fps"] == runtime_default


def test_load_fps_invalid_negative_falls_back_with_warning(monkeypatch, caplog):
    """Negative FPS should be rejected and replaced with default fallback."""
    monkeypatch.setenv("MIO_FPS", "-1")

    with caplog.at_level("WARNING"):
        camera_config = runtime_config._load_camera_config()

    assert camera_config["fps"] == 24
    assert camera_config["target_fps"] == 24
    assert "Invalid MIO_FPS range" in caplog.text


def test_load_fps_out_of_range_falls_back_with_warning(monkeypatch, caplog):
    """FPS values above schema maximum should be rejected and replaced with default."""
    monkeypatch.setenv("MIO_FPS", "9999")

    with caplog.at_level("WARNING"):
        camera_config = runtime_config._load_camera_config()

    assert camera_config["fps"] == 24
    assert camera_config["target_fps"] == 24
    assert "Invalid MIO_FPS range" in caplog.text


def test_load_fps_non_integer_falls_back_with_warning(monkeypatch, caplog):
    """Non-integer FPS should be rejected and replaced with default fallback."""
    monkeypatch.setenv("MIO_FPS", "not-an-int")

    with caplog.at_level("WARNING"):
        camera_config = runtime_config._load_camera_config()

    assert camera_config["fps"] == 24
    assert camera_config["target_fps"] == 24
    assert "Invalid MIO_FPS value" in caplog.text


def test_load_env_config_defaults_to_default_performance_profile(monkeypatch):
    """Runtime config should expose the explicit default performance profile."""
    monkeypatch.delenv("MIO_PERFORMANCE_PROFILE", raising=False)
    monkeypatch.delenv("MIO_PI3_PROFILE", raising=False)

    cfg = runtime_config.load_env_config()

    assert cfg["performance_profile"] == "default"
    assert cfg["pi3_profile_enabled"] is False
    assert cfg["fps"] == 24


def test_load_env_config_applies_pi3_performance_profile_defaults(monkeypatch):
    """pi3 performance profile should apply conservative camera defaults."""
    monkeypatch.setenv("MIO_PERFORMANCE_PROFILE", "pi3")
    monkeypatch.delenv("MIO_FPS", raising=False)
    monkeypatch.delenv("MIO_TARGET_FPS", raising=False)
    monkeypatch.delenv("MIO_JPEG_QUALITY", raising=False)
    monkeypatch.delenv("MIO_MAX_STREAM_CONNECTIONS", raising=False)

    cfg = runtime_config.load_env_config()

    assert cfg["performance_profile"] == "pi3"
    assert cfg["pi3_profile_enabled"] is True
    assert cfg["fps"] == 12
    assert cfg["target_fps"] == 12
    assert cfg["jpeg_quality"] == 75
    assert cfg["max_stream_connections"] == 3


def test_load_env_config_env_values_override_profile_defaults(monkeypatch):
    """Explicit env vars must override profile-provided defaults."""
    monkeypatch.setenv("MIO_PERFORMANCE_PROFILE", "pi3")
    monkeypatch.setenv("MIO_FPS", "20")
    monkeypatch.setenv("MIO_TARGET_FPS", "8")
    monkeypatch.setenv("MIO_JPEG_QUALITY", "88")
    monkeypatch.setenv("MIO_MAX_STREAM_CONNECTIONS", "9")

    cfg = runtime_config.load_env_config()

    assert cfg["performance_profile"] == "pi3"
    assert cfg["fps"] == 20
    assert cfg["target_fps"] == 8
    assert cfg["jpeg_quality"] == 88
    assert cfg["max_stream_connections"] == 9


def test_load_env_config_legacy_pi3_profile_maps_to_preset_with_warning(monkeypatch, caplog):
    """Legacy MIO_PI3_PROFILE should map to pi3 preset and emit deprecation warning."""
    monkeypatch.delenv("MIO_PERFORMANCE_PROFILE", raising=False)
    monkeypatch.setenv("MIO_PI3_PROFILE", "true")

    with caplog.at_level("WARNING"):
        cfg = runtime_config.load_env_config()

    assert cfg["performance_profile"] == "pi3"
    assert cfg["pi3_profile_enabled"] is True
    assert "MIO_PI3_PROFILE is deprecated" in caplog.text


def test_load_env_config_invalid_performance_profile_raises(monkeypatch):
    """Unknown performance profile values should fail fast with clear error."""
    monkeypatch.setenv("MIO_PERFORMANCE_PROFILE", "turbo")

    with pytest.raises(ValueError, match="Invalid MIO_PERFORMANCE_PROFILE"):
        runtime_config.load_env_config()


def test_load_env_config_defaults_camera_init_failure_to_graceful(monkeypatch):
    """Camera init failure handling should default to graceful startup."""
    monkeypatch.delenv("MIO_FAIL_ON_CAMERA_INIT_ERROR", raising=False)
    monkeypatch.delenv("MIO_CAMERA_INIT_REQUIRED", raising=False)

    cfg = runtime_config.load_env_config()

    assert cfg["fail_on_camera_init_error"] is False


def test_load_env_config_enables_strict_camera_init_failure_mode(monkeypatch):
    """Strict startup mode should be enabled via the primary env var."""
    monkeypatch.setenv("MIO_FAIL_ON_CAMERA_INIT_ERROR", "true")
    monkeypatch.delenv("MIO_CAMERA_INIT_REQUIRED", raising=False)

    cfg = runtime_config.load_env_config()

    assert cfg["fail_on_camera_init_error"] is True


def test_load_env_config_supports_legacy_camera_init_required_alias(monkeypatch):
    """Legacy camera init strictness env var alias should still be honored."""
    monkeypatch.delenv("MIO_FAIL_ON_CAMERA_INIT_ERROR", raising=False)
    monkeypatch.setenv("MIO_CAMERA_INIT_REQUIRED", "yes")

    cfg = runtime_config.load_env_config()

    assert cfg["fail_on_camera_init_error"] is True


def test_merge_config_with_persisted_settings_does_not_override_runtime_feature_flags():
    """Persisted feature flags should not override runtime feature flag values."""
    env_config = {
        "fps": 24,
        "target_fps": 24,
        "jpeg_quality": 90,
        "discovery_interval_seconds": 30.0,
        "discovery_management_url": "http://127.0.0.1:8001",
        "mock_camera": False,
    }
    persisted = {
        "settings": {
            "camera": {},
            "feature_flags": {"MOCK_CAMERA": True},
            "discovery": {},
            "logging": {},
        }
    }

    merged = runtime_config.merge_config_with_persisted_settings(env_config, persisted)

    assert merged["mock_camera"] is False


def test_get_effective_settings_payload_reads_feature_flags_from_runtime(monkeypatch):
    """Effective payload should report runtime feature flags, not persisted values."""
    env_config = {
        "app_mode": "webcam",
        "resolution": (640, 480),
        "fps": 24,
        "target_fps": 24,
        "jpeg_quality": 90,
        "max_frame_age_seconds": 10.0,
        "max_stream_connections": 10,
        "api_test_mode_enabled": False,
        "api_test_cycle_interval_seconds": 5.0,
        "discovery_enabled": False,
        "discovery_management_url": "http://127.0.0.1:8001",
        "discovery_token": "",
        "discovery_interval_seconds": 30.0,
        "discovery_webcam_id": "",
        "log_level": "INFO",
        "log_format": "text",
        "log_include_identifiers": False,
        "cors_enabled": True,
        "cors_origins": "*",
        "bind_host": "127.0.0.1",
        "bind_port": 8000,
        "pi3_profile_enabled": False,
        "mock_camera": False,
        "pykms_mock_fallback_enabled": False,
        "node_registry_path": "/data/node-registry.json",
        "application_settings_path": "/data/application-settings.json",
        "management_auth_token": "",
        "webcam_control_plane_auth_token": "",
    }

    class StaticStore:
        def load(self):
            return {
                "settings": {
                    "camera": {},
                    "feature_flags": {"MOCK_CAMERA": False},
                    "logging": {},
                    "discovery": {},
                }
            }

    monkeypatch.setattr(runtime_config, "load_env_config", lambda: env_config)
    monkeypatch.setattr(
        runtime_config,
        "is_flag_enabled",
        lambda flag_name: {"MOCK_CAMERA": True}[flag_name],
    )

    payload = runtime_config.get_effective_settings_payload(StaticStore())

    assert payload["settings"]["feature_flags"] == {"MOCK_CAMERA": True}


def test_load_env_config_enables_pykms_fallback_in_api_test_mode(monkeypatch):
    """Internal pykms fallback should be enabled automatically in API test mode."""
    monkeypatch.setenv("MIO_API_TEST_MODE_ENABLED", "true")

    cfg = runtime_config.load_env_config()

    assert cfg["pykms_mock_fallback_enabled"] is True


def test_load_env_config_enables_pykms_fallback_under_pytest(monkeypatch):
    """Internal pykms fallback should be enabled automatically during pytest runs."""
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_runtime_config.py::test_example")

    cfg = runtime_config.load_env_config()

    assert cfg["pykms_mock_fallback_enabled"] is True


def test_load_env_config_supports_changelog_remote_config(monkeypatch):
    """Changelog remote URL and timeout should be exposed in runtime configuration."""
    monkeypatch.setenv("MIO_CHANGELOG_REMOTE_URL", "https://example.com/CHANGELOG.md")
    monkeypatch.setenv("MIO_CHANGELOG_REMOTE_TIMEOUT_SECONDS", "7.5")

    cfg = runtime_config.load_env_config()

    assert cfg["changelog_remote_url"] == "https://example.com/CHANGELOG.md"
    assert cfg["changelog_remote_timeout_seconds"] == 7.5


def test_load_env_config_changelog_timeout_invalid_falls_back(monkeypatch):
    """Invalid changelog timeout should fallback to default value."""
    monkeypatch.setenv("MIO_CHANGELOG_REMOTE_TIMEOUT_SECONDS", "bad")

    cfg = runtime_config.load_env_config()

    assert cfg["changelog_remote_timeout_seconds"] == 3.0
