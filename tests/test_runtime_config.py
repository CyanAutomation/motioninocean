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
        "cat_gif_enabled": False,
        "cataas_api_url": "https://cataas.com/cat.gif",
        "cat_gif_cache_ttl_seconds": 60.0,
        "cat_gif_retry_base_seconds": 1.0,
        "cat_gif_retry_max_seconds": 60.0,
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
        "allow_pykms_mock": False,
        "node_registry_path": "/data/node-registry.json",
        "application_settings_path": "/data/application-settings.json",
        "management_auth_token": "",
    }

    monkeypatch.setattr(runtime_config, "load_env_config", lambda: env_config)

    snapshot = {
        "settings": {
            "camera": {"fps": 42},
            "feature_flags": {"FLAG_A": True},
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
                    "feature_flags": {"FLAG_A": False},
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
    assert payload["settings"]["feature_flags"] == {"FLAG_A": True}
    assert payload["last_modified"] == "2026-01-01T00:00:00+00:00"
    assert payload["modified_by"] == "api_patch"


def test_load_env_config_supports_application_settings_path(monkeypatch):
    """APPLICATION_SETTINGS_PATH should be exposed in runtime configuration."""
    monkeypatch.setenv("APPLICATION_SETTINGS_PATH", "/tmp/custom-settings.json")

    cfg = runtime_config.load_env_config()

    assert cfg["application_settings_path"] == "/tmp/custom-settings.json"


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
    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("MOCK_CAMERA", "true")
    monkeypatch.setenv("WEBCAM_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("APPLICATION_SETTINGS_PATH", str(settings_path))

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
