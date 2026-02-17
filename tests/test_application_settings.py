"""
Tests for ApplicationSettings persistence layer
"""

import json

# Import from parent directory
import sys
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent / "pi_camera_in_docker"))

from application_settings import ApplicationSettings, SettingsValidationError


@pytest.fixture
def temp_settings_file():
    """Create a temporary settings file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)
    Path(f"{temp_path}.lock").unlink(missing_ok=True)


class TestApplicationSettingsBasic:
    """Test basic ApplicationSettings operations."""

    def test_init_creates_path(self, temp_settings_file):
        """Test that ApplicationSettings creates path if needed."""
        settings = ApplicationSettings(temp_settings_file)
        assert settings.path == Path(temp_settings_file)

    def test_load_default_schema(self, temp_settings_file):
        """Test loading default schema when no file exists."""
        settings = ApplicationSettings(temp_settings_file)
        data = settings.load()

        assert data["version"] == 1
        assert "settings" in data
        assert "camera" in data["settings"]
        assert "feature_flags" in data["settings"]
        assert "logging" in data["settings"]
        assert "discovery" in data["settings"]

    def test_save_and_load(self, temp_settings_file):
        """Test saving and loading settings."""
        settings = ApplicationSettings(temp_settings_file)

        # Save some settings
        new_settings = {
            "camera": {
                "fps": 60,
                "jpeg_quality": 80,
            },
            "feature_flags": {
                "PROMETHEUS_METRICS": True,
            },
            "logging": {
                "log_level": "DEBUG",
            },
            "discovery": {},
        }

        settings.save(new_settings, modified_by="test")

        # Load and verify
        loaded = settings.load()
        assert loaded["settings"]["camera"]["fps"] == 60
        assert loaded["settings"]["camera"]["jpeg_quality"] == 80
        assert loaded["settings"]["feature_flags"]["PROMETHEUS_METRICS"] is True
        assert loaded["settings"]["logging"]["log_level"] == "DEBUG"
        assert loaded["modified_by"] == "test"


class TestApplicationSettingsGetSet:
    """Test get/set operations."""

    def test_get_single_value(self, temp_settings_file):
        """Test getting a single setting value."""
        settings = ApplicationSettings(temp_settings_file)
        settings.set("camera", "fps", 60, "test")

        value = settings.get("camera", "fps")
        assert value == 60

    def test_get_default_when_not_set(self, temp_settings_file):
        """Test getting default when value not set."""
        settings = ApplicationSettings(temp_settings_file)
        value = settings.get("camera", "fps", default=30)
        assert value == 30

    def test_set_multiple_in_category(self, temp_settings_file):
        """Test updating multiple settings in a category."""
        settings = ApplicationSettings(temp_settings_file)

        updates = {
            "fps": 60,
            "jpeg_quality": 85,
        }
        settings.update_category("camera", updates, "test")

        assert settings.get("camera", "fps") == 60
        assert settings.get("camera", "jpeg_quality") == 85

    def test_set_invalid_category_raises(self, temp_settings_file):
        """Test that setting invalid category raises error."""
        settings = ApplicationSettings(temp_settings_file)

        with pytest.raises(SettingsValidationError):
            settings.set("invalid_category", "key", "value")

    def test_set_invalid_property_raises(self, temp_settings_file):
        """Test that setting invalid property in known category raises error."""
        settings = ApplicationSettings(temp_settings_file)

        with pytest.raises(SettingsValidationError):
            settings.set("camera", "invalid_property", "value")


class TestApplicationSettingsFeatureFlags:
    """Test feature flag handling (dynamic keys)."""

    def test_set_feature_flag(self, temp_settings_file):
        """Test setting feature flags (which have dynamic keys)."""
        settings = ApplicationSettings(temp_settings_file)

        # Feature flags can have arbitrary keys
        settings.set("feature_flags", "CUSTOM_FLAG", True, "test")
        assert settings.get("feature_flags", "CUSTOM_FLAG") is True

    def test_update_feature_flags(self, temp_settings_file):
        """Test updating multiple feature flags."""
        settings = ApplicationSettings(temp_settings_file)

        flags = {
            "PROMETHEUS_METRICS": True,
            "DEBUG_LOGGING": False,
        }
        settings.update_category("feature_flags", flags, "test")

        assert settings.get("feature_flags", "PROMETHEUS_METRICS") is True
        assert settings.get("feature_flags", "DEBUG_LOGGING") is False


class TestApplicationSettingsReset:
    """Test reset functionality."""

    def test_reset_clears_file(self, temp_settings_file):
        """Test that reset clears the settings file."""
        settings = ApplicationSettings(temp_settings_file)

        # Set some values
        settings.set("camera", "fps", 60, "test")
        assert Path(temp_settings_file).exists()

        # Reset
        settings.reset()
        assert not Path(temp_settings_file).exists()

    def test_load_after_reset_returns_defaults(self, temp_settings_file):
        """Test that loading after reset returns default schema."""
        settings = ApplicationSettings(temp_settings_file)

        # Set and reset
        settings.set("camera", "fps", 60, "test")
        settings.reset()

        # Load should return defaults
        loaded = settings.load()
        assert loaded["settings"]["camera"]["fps"] is None

    def test_load_coerces_invalid_feature_flags_to_empty_dict(self, temp_settings_file):
        """Invalid persisted feature_flags values are treated as empty maps."""
        settings = ApplicationSettings(temp_settings_file)

        with open(temp_settings_file, "w") as f:
            json.dump(
                {
                    "version": 1,
                    "settings": {
                        "camera": {},
                        "feature_flags": ["invalid"],
                        "logging": {},
                        "discovery": {},
                    },
                },
                f,
            )

        loaded = settings.load()
        assert loaded["settings"]["feature_flags"] == {}


class TestApplicationSettingsChanges:
    """Test change tracking."""

    def test_get_changes_shows_overrides(self, temp_settings_file):
        """Test that get_changes_from_env shows overridden values."""
        settings = ApplicationSettings(temp_settings_file)

        # Save an override
        new_settings = {
            "camera": {"fps": 60},
            "feature_flags": {},
            "logging": {},
            "discovery": {},
        }
        settings.save(new_settings, "test")

        # Get changes with env defaults
        env_defaults = {
            "camera": {"fps": 30},
            "feature_flags": {},
            "logging": {},
            "discovery": {},
        }

        changes = settings.get_changes_from_env(env_defaults)
        assert len(changes["overridden"]) > 0

        override = next((o for o in changes["overridden"] if o["key"] == "fps"), None)
        assert override is not None
        assert override["value"] == 60
        assert override["env_value"] == 30

    def test_get_changes_handles_invalid_feature_flag_maps(self, temp_settings_file):
        """Non-dict feature flag maps are treated as empty during diffing."""
        settings = ApplicationSettings(temp_settings_file)

        with open(temp_settings_file, "w") as f:
            json.dump(
                {
                    "version": 1,
                    "settings": {
                        "camera": {},
                        "feature_flags": "not-a-dict",
                        "logging": {},
                        "discovery": {},
                    },
                },
                f,
            )

        changes = settings.get_changes_from_env({"feature_flags": "bad-env-type"})
        feature_flag_changes = [
            c for c in changes["overridden"] if c["category"] == "feature_flags"
        ]
        assert feature_flag_changes == []


class TestApplicationSettingsValidation:
    """Test settings validation."""

    def test_invalid_root_type_raises(self, temp_settings_file):
        """Test that non-dict root raises error."""
        settings = ApplicationSettings(temp_settings_file)

        with pytest.raises(SettingsValidationError):
            settings.save([1, 2, 3])  # type: ignore

    def test_missing_required_categories_raises(self, temp_settings_file):
        """Test that missing categories raises error."""
        settings = ApplicationSettings(temp_settings_file)

        with pytest.raises(SettingsValidationError):
            settings.save({"camera": {}})  # type: ignore

    def test_invalid_version_raises(self, temp_settings_file):
        """Test that invalid version in file raises error on load."""
        settings = ApplicationSettings(temp_settings_file)

        # Create file with invalid version
        with open(temp_settings_file, "w") as f:
            json.dump(
                {
                    "version": 99,
                    "settings": {"camera": {}, "feature_flags": {}, "logging": {}, "discovery": {}},
                },
                f,
            )

        # Trying to load invalid version should raise
        with pytest.raises(SettingsValidationError):
            settings.load()


class TestApplicationSettingsConcurrency:
    """Test file locking for concurrent access."""

    def test_concurrent_save_safe(self, temp_settings_file):
        """Test that concurrent saves use file locking."""
        settings1 = ApplicationSettings(temp_settings_file)
        settings2 = ApplicationSettings(temp_settings_file)

        # Save from both instances
        settings1.save(
            {
                "camera": {"fps": 60},
                "feature_flags": {},
                "logging": {},
                "discovery": {},
            },
            "test1",
        )

        settings2.save(
            {
                "camera": {"fps": 45},
                "feature_flags": {},
                "logging": {},
                "discovery": {},
            },
            "test2",
        )

        # Should have one of the saves (last one wins)
        loaded = settings1.load()
        assert loaded["settings"]["camera"]["fps"] in [60, 45]

    def test_concurrent_set_keeps_updates_to_different_keys(self, temp_settings_file):
        """Concurrent set operations on different keys should both persist."""
        settings = ApplicationSettings(temp_settings_file)
        start = threading.Barrier(2)

        def set_fps():
            start.wait()
            settings.set("camera", "fps", 60, "thread_fps")

        def set_quality():
            start.wait()
            settings.set("camera", "jpeg_quality", 85, "thread_quality")

        thread_a = threading.Thread(target=set_fps)
        thread_b = threading.Thread(target=set_quality)
        thread_a.start()
        thread_b.start()
        thread_a.join()
        thread_b.join()

        loaded = settings.load()
        assert loaded["settings"]["camera"]["fps"] == 60
        assert loaded["settings"]["camera"]["jpeg_quality"] == 85

    def test_concurrent_update_category_keeps_updates_to_different_keys(self, temp_settings_file):
        """Concurrent category updates should preserve all independent key changes."""
        settings = ApplicationSettings(temp_settings_file)
        start = threading.Barrier(2)

        def update_camera_fps():
            start.wait()
            settings.update_category("camera", {"fps": 48}, "thread_fps")

        def update_camera_quality():
            start.wait()
            settings.update_category("camera", {"jpeg_quality": 70}, "thread_quality")

        thread_a = threading.Thread(target=update_camera_fps)
        thread_b = threading.Thread(target=update_camera_quality)
        thread_a.start()
        thread_b.start()
        thread_a.join()
        thread_b.join()

        loaded = settings.load()
        assert loaded["settings"]["camera"]["fps"] == 48
        assert loaded["settings"]["camera"]["jpeg_quality"] == 70

    def test_custom_settings_path_creates_lock_file_next_to_settings_file(self, tmp_path):
        """Custom settings paths should create lock files in the same directory."""
        settings_path = tmp_path / "restricted" / "application-settings.json"
        settings = ApplicationSettings(str(settings_path))

        settings.save(
            {
                "camera": {"fps": 30},
                "feature_flags": {},
                "logging": {},
                "discovery": {},
            },
            "test",
        )

        assert settings_path.exists()
        assert (settings_path.parent / f"{settings_path.name}.lock").exists()

    def test_load_acquires_lock(self, temp_settings_file, monkeypatch):
        """Load should acquire the settings lock before reading."""
        settings = ApplicationSettings(temp_settings_file)
        lock_used = {"value": False}

        @contextmanager
        def tracked_lock():
            lock_used["value"] = True
            yield

        monkeypatch.setattr(settings, "_exclusive_lock", tracked_lock)

        settings.load()
        assert lock_used["value"] is True

    def test_load_handles_file_removed_after_exists_check(self, temp_settings_file, monkeypatch):
        """Load should return defaults when file disappears during read."""
        settings = ApplicationSettings(temp_settings_file)

        # Ensure the file exists so load reaches read_text.
        Path(temp_settings_file).write_text("{}", encoding="utf-8")

        def raise_file_not_found(*args, **kwargs):
            raise FileNotFoundError("settings file disappeared")

        monkeypatch.setattr(Path, "read_text", raise_file_not_found)

        loaded = settings.load()
        assert loaded == settings._clone_schema()


class TestApplicationSettingsPermissionErrors:
    """Test permission-denied error guidance for settings paths."""

    def test_init_permission_error_logs_and_continues(self, monkeypatch, tmp_path, caplog):
        """Init should preserve existing contract and not fail on permission errors."""
        target_path = tmp_path / "no-write" / "application-settings.json"

        def deny_mkdir(self, *args, **kwargs):
            raise PermissionError("permission denied")

        monkeypatch.setattr(Path, "mkdir", deny_mkdir)

        with caplog.at_level("DEBUG"):
            settings = ApplicationSettings(str(target_path))

        assert settings.path == target_path
        assert f"Could not create settings directory {target_path.parent}" in caplog.text

    def test_save_permission_error_has_actionable_guidance(self, temp_settings_file, monkeypatch):
        """Save should raise guidance when write is permission denied."""
        settings = ApplicationSettings(temp_settings_file)

        def deny_save(*args, **kwargs):
            raise PermissionError("permission denied")

        monkeypatch.setattr(settings, "_save_atomic", deny_save)

        with pytest.raises(SettingsValidationError) as exc_info:
            settings.set("camera", "fps", 30, "test")

        message = str(exc_info.value)
        assert temp_settings_file in message
        assert "Check /data mount ownership" in message
        assert "APPLICATION_SETTINGS_PATH" in message

    def test_load_permission_error_has_actionable_guidance(self, temp_settings_file, monkeypatch):
        """Load should raise guidance when lock acquisition is permission denied."""
        settings = ApplicationSettings(temp_settings_file)

        def deny_open(self, *args, **kwargs):
            raise PermissionError("permission denied")

        monkeypatch.setattr(Path, "open", deny_open)

        with pytest.raises(SettingsValidationError) as exc_info:
            settings.load()

        message = str(exc_info.value)
        assert "Check /data mount ownership" in message
        assert "APPLICATION_SETTINGS_PATH" in message


class TestApplicationSettingsFileCorruption:
    """Test handling of corrupted files."""

    def test_corrupted_json_raises(self, temp_settings_file):
        """Test that corrupted JSON raises error."""
        settings = ApplicationSettings(temp_settings_file)

        # Write invalid JSON
        with open(temp_settings_file, "w") as f:
            f.write("{ invalid json }")

        with pytest.raises(SettingsValidationError):
            settings.load()

    def test_corrupted_file_recovery(self, temp_settings_file):
        """Test that corrupted file doesn't prevent reset."""
        settings = ApplicationSettings(temp_settings_file)

        # Write invalid JSON
        with open(temp_settings_file, "w") as f:
            f.write("{ invalid json }")

        # Reset should still work
        settings.reset()
        assert not Path(temp_settings_file).exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
