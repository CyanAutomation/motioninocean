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
        "discovery_node_id": "",
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
