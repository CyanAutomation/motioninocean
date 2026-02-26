import pytest

from pi_camera_in_docker import runtime_config


def test_load_target_fps_non_numeric_falls_back_to_fps(monkeypatch, caplog):
    """Non-numeric target FPS should fall back to parsed fps value."""
    monkeypatch.setenv("MIO_FPS", "30")
    monkeypatch.setenv("MIO_TARGET_FPS", "not-a-number")

    with caplog.at_level("WARNING"):
        camera_config = runtime_config._load_camera_config()

    assert camera_config["fps"] == 30
    assert camera_config["target_fps"] == 30
    assert "Invalid MIO_TARGET_FPS value" in caplog.text


@pytest.mark.parametrize("invalid_target", ["0", "-5"])
def test_load_target_fps_non_positive_falls_back_to_fps(monkeypatch, caplog, invalid_target):
    """Zero and negative target FPS values should fall back to fps."""
    monkeypatch.setenv("MIO_FPS", "28")
    monkeypatch.setenv("MIO_TARGET_FPS", invalid_target)

    with caplog.at_level("WARNING"):
        camera_config = runtime_config._load_camera_config()

    assert camera_config["fps"] == 28
    assert camera_config["target_fps"] == 28
    assert "Invalid MIO_TARGET_FPS range" in caplog.text


def test_load_target_fps_over_limit_falls_back_to_fps(monkeypatch, caplog):
    """Target FPS values over max range should fall back to fps."""
    monkeypatch.setenv("MIO_FPS", "26")
    monkeypatch.setenv("MIO_TARGET_FPS", "121")

    with caplog.at_level("WARNING"):
        camera_config = runtime_config._load_camera_config()

    assert camera_config["fps"] == 26
    assert camera_config["target_fps"] == 26
    assert "Invalid MIO_TARGET_FPS range" in caplog.text


def test_load_target_fps_valid_value_is_preserved(monkeypatch, caplog):
    """Valid target FPS should be applied and should not trigger fallback warnings."""
    monkeypatch.setenv("MIO_FPS", "20")
    monkeypatch.setenv("MIO_TARGET_FPS", "15")

    with caplog.at_level("WARNING"):
        camera_config = runtime_config._load_camera_config()

    assert camera_config["fps"] == 20
    assert camera_config["target_fps"] == 15
    assert "Invalid MIO_TARGET_FPS" not in caplog.text


def test_merge_config_with_persisted_settings_env_fps_wins(monkeypatch):
    """Explicit MIO_FPS should override persisted camera fps."""
    monkeypatch.setenv("MIO_FPS", "33")

    env_config = runtime_config.load_env_config()
    persisted = {"settings": {"camera": {"fps": 12}}}

    merged = runtime_config.merge_config_with_persisted_settings(env_config, persisted)

    assert merged["fps"] == 33


def test_merge_config_with_persisted_settings_env_logging_wins(monkeypatch):
    """Explicit MIO_LOG_LEVEL should override persisted logging level."""
    monkeypatch.setenv("MIO_LOG_LEVEL", "ERROR")

    env_config = runtime_config.load_env_config()
    persisted = {"settings": {"logging": {"log_level": "DEBUG"}}}

    merged = runtime_config.merge_config_with_persisted_settings(env_config, persisted)

    assert merged["log_level"] == "ERROR"


def test_merge_config_with_persisted_settings_persisted_used_when_env_unset(monkeypatch):
    """Persisted editable settings should apply when env var is not explicitly set."""
    monkeypatch.delenv("MIO_FPS", raising=False)

    env_config = runtime_config.load_env_config()
    persisted = {"settings": {"camera": {"fps": 12}}}

    merged = runtime_config.merge_config_with_persisted_settings(env_config, persisted)

    assert merged["fps"] == 12


def test_merge_config_with_persisted_settings_uses_explicit_env_var_snapshot(monkeypatch):
    """Explicit env snapshot should be authoritative for overlay behavior."""
    monkeypatch.setenv("MIO_LOG_LEVEL", "ERROR")
    env_config = runtime_config.load_env_config()
    monkeypatch.delenv("MIO_LOG_LEVEL", raising=False)

    persisted = {"settings": {"logging": {"log_level": "DEBUG"}}}
    merged_without_snapshot = runtime_config.merge_config_with_persisted_settings(
        env_config, persisted
    )
    merged_with_snapshot = runtime_config.merge_config_with_persisted_settings(
        env_config,
        persisted,
        explicit_env_vars={"MIO_LOG_LEVEL"},
    )

    assert merged_without_snapshot["log_level"] == "DEBUG"
    assert merged_with_snapshot["log_level"] == "ERROR"
