"""
Application Settings Management
Persists runtime configuration changes to disk (/data/application-settings.json).
Follows the same file-locking pattern as node_registry.py for atomic operations.
"""

import json
import logging
import os
import tempfile
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar, Dict

import sentry_sdk


try:
    import fcntl
except ImportError:  # pragma: no cover - unavailable on non-POSIX
    fcntl = None

try:
    import msvcrt
except ImportError:  # pragma: no cover - unavailable on non-Windows
    msvcrt = None


logger = logging.getLogger(__name__)

# Error messages for settings validation
_ERROR_ROOT_NOT_DICT = "Root must be a dict"
_ERROR_SETTINGS_NOT_DICT = "'settings' must be a dict"
_ERROR_CAMERA_NOT_DICT = "'settings.camera' must be a dict"
_ERROR_FEATURE_FLAGS_NOT_DICT = "'settings.feature_flags' must be a dict"
_ERROR_LOGGING_NOT_DICT = "'settings.logging' must be a dict"
_ERROR_DISCOVERY_NOT_DICT = "'settings.discovery' must be a dict"


class SettingsValidationError(ValueError):
    """Raised when settings validation fails."""


def _permission_guidance(path: Path, operation: str) -> str:
    """Build actionable guidance for permission-denied settings operations."""
    return (
        f"Permission denied while {operation} at '{path}'. "
        "Check /data mount ownership and write permissions for the container user, "
        "or set APPLICATION_SETTINGS_PATH to a writable location "
        "(for example, ./data/application-settings.json)."
    )


class ApplicationSettings:
    """
    Manages persistent application settings stored in JSON file.

    Settings are organized by category:
    - camera: resolution, fps, jpeg_quality, max_stream_connections, max_frame_age_seconds
    - feature_flags: MIO_* feature toggle flags
    - logging: log_level, log_format, log_include_identifiers
    - discovery: discovery_enabled, discovery_management_url, discovery_token, discovery_interval_seconds

    Uses file-based locking so each mutating operation performs an atomic
    read-modify-write cycle across threads/processes.
    """

    DEFAULT_SCHEMA: ClassVar = {
        "version": 1,
        "settings": {
            "camera": {
                "resolution": None,  # "1280x720" format, null = use env default
                "fps": None,
                "jpeg_quality": None,
                "max_stream_connections": None,
                "max_frame_age_seconds": None,
            },
            "feature_flags": {},  # Dict of {flag_name: bool}
            "logging": {
                "log_level": None,
                "log_format": None,
                "log_include_identifiers": None,
            },
            "discovery": {
                "discovery_enabled": None,
                "discovery_management_url": None,
                "discovery_token": None,
                "discovery_interval_seconds": None,
            },
        },
        "last_modified": None,
        "modified_by": "system",  # Track which component made last change
    }

    def __init__(self, path: str = "/data/application-settings.json"):
        """
        Initialize ApplicationSettings with file path.

        Args:
            path: Path to JSON settings file. Defaults to /data/application-settings.json
        """
        self.path = Path(path)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # In test environments or restricted permissions, directory creation may fail.
            # This is non-fatal; subsequent operations will raise actionable errors as needed.
            logger.debug("Could not create settings directory %s: %s", self.path.parent, e)

    def load(self) -> Dict[str, Any]:
        """
        Load settings from disk. Returns merged schema with persisted values.

        Returns:
            Dict with 'version', 'settings', 'last_modified', 'modified_by' keys

        Raises:
            SettingsValidationError: If file is corrupted or invalid
        """
        try:
            with self._exclusive_lock():
                return self._load_unlocked()
        except SettingsValidationError:
            raise
        except Exception as exc:
            logger.error("Failed to load settings: %s", exc)
            message = f"Failed to load settings: {exc}"
            raise SettingsValidationError(message) from exc

    def _load_unlocked(self) -> Dict[str, Any]:
        """Load settings from disk without acquiring the file lock."""
        if not self.path.exists():
            return self._clone_schema()

        try:
            try:
                content = self.path.read_text(encoding="utf-8").strip()
            except PermissionError as exc:
                message = _permission_guidance(self.path, "reading settings file")
                logger.error(message)
                raise SettingsValidationError(message) from exc
            except (FileNotFoundError, OSError):
                # File may be removed/replaced after the existence check during
                # concurrent reset/write operations; treat this as "no settings".
                return self._clone_schema()

            if not content:  # Handle empty files gracefully
                return self._clone_schema()

            raw = json.loads(content)

            self._validate_settings_structure(raw)

            schema = self._clone_schema()

            settings = raw.get("settings", {})

            # Merge persisted settings, keeping schema structure
            schema["settings"]["camera"] = {
                **schema["settings"]["camera"],
                **{k: v for k, v in settings["camera"].items() if k in schema["settings"]["camera"]},
            }
            schema["settings"]["feature_flags"] = settings["feature_flags"]
            schema["settings"]["logging"] = {
                **schema["settings"]["logging"],
                **{k: v for k, v in settings["logging"].items() if k in schema["settings"]["logging"]},
            }
            schema["settings"]["discovery"] = {
                **schema["settings"]["discovery"],
                **{
                    k: v
                    for k, v in settings["discovery"].items()
                    if k in schema["settings"]["discovery"]
                },
            }

            if raw.get("last_modified"):
                schema["last_modified"] = raw["last_modified"]
            if raw.get("modified_by"):
                schema["modified_by"] = raw["modified_by"]

        except json.JSONDecodeError as exc:
            logger.error("Corrupted settings file %s: %s", self.path, exc)
            message = f"Corrupted settings file: {exc}"
            raise SettingsValidationError(message) from exc
        else:
            return schema

    def save(self, settings: Dict[str, Any], modified_by: str = "system") -> None:
        """
        Save settings to disk atomically.

        Args:
            settings: Dict with 'settings' key containing camera/feature_flags/logging/discovery
            modified_by: Label for who made this change (e.g., "api", "ui", "system")

        Raises:
            SettingsValidationError: If validation fails
        """
        # Enrich an isolated scope so these tags don't bleed into other events
        # when save() is called from background threads or tests.
        with sentry_sdk.new_scope() as scope:
            scope.set_tag("component", "settings")
            scope.set_context(
                "settings_operation",
                {
                    "modified_by": modified_by,
                },
            )

            data = {
                "version": 1,
                "settings": settings,
                "last_modified": datetime.now(timezone.utc).isoformat(),
                "modified_by": modified_by,
            }

            try:
                self._validate_settings_structure(data)
            except Exception as exc:
                logger.error("Settings validation failed: %s", exc)
                message = f"Invalid settings structure: {exc}"
                raise SettingsValidationError(message) from exc

            with self._exclusive_lock():
                self._save_atomic(data)
                logger.info("Settings saved by %s", modified_by)

    def get(self, category: str, key: str, default: Any = None) -> Any:
        """
        Get a single setting value.

        Args:
            category: Category name (camera, feature_flags, logging, discovery)
            key: Setting key within category
            default: Default value if not found

        Returns:
            Setting value or default (treating None as unset)
        """
        data = self.load()
        try:
            value = data["settings"][category].get(key, default)
        except (KeyError, AttributeError):
            return default
        else:
            # Treat None as "unset", return default instead
            return default if value is None else value

    def set(self, category: str, key: str, value: Any, modified_by: str = "system") -> None:
        """
        Set a single setting value and persist.

        Args:
            category: Category name
            key: Setting key within category
            value: New value
            modified_by: Label for who made this change

        Raises:
            SettingsValidationError: If key/category invalid
        """
        with self._exclusive_lock():
            data = self._load_unlocked()
            if category not in data["settings"]:
                message = f"Unknown settings category: {category}"
                raise SettingsValidationError(message)

            if category == "feature_flags":
                # Feature flags are dynamic; create entry if needed
                data["settings"][category][key] = value
            else:
                # Other categories have fixed schema
                if key not in data["settings"][category]:
                    message = f"Unknown settings key '{key}' in category '{category}'"
                    raise SettingsValidationError(message)
                data["settings"][category][key] = value

            data["last_modified"] = datetime.now(timezone.utc).isoformat()
            data["modified_by"] = modified_by
            self._save_atomic(data)

    def update_category(
        self, category: str, updates: Dict[str, Any], modified_by: str = "system"
    ) -> None:
        """
        Update multiple settings in a category.

        Args:
            category: Category name
            updates: Dict of {key: value} updates
            modified_by: Label for who made this change

        Raises:
            SettingsValidationError: If any key invalid
        """
        with self._exclusive_lock():
            data = self._load_unlocked()
            if category not in data["settings"]:
                message = f"Unknown settings category: {category}"
                raise SettingsValidationError(message)

            if category == "feature_flags":
                data["settings"][category].update(updates)
            else:
                # Validate all keys exist
                for key in updates:
                    if key not in data["settings"][category]:
                        message = f"Unknown settings key '{key}' in category '{category}'"
                        raise SettingsValidationError(message)
                data["settings"][category].update(updates)

            data["last_modified"] = datetime.now(timezone.utc).isoformat()
            data["modified_by"] = modified_by
            self._save_atomic(data)

    def apply_patch_atomic(
        self, patch: Dict[str, Any], modified_by: str = "system"
    ) -> Dict[str, Any]:
        """Apply a validated settings patch and persist as one locked operation."""
        with self._exclusive_lock():
            data = self._load_unlocked()
            current_settings = data.setdefault("settings", {})

            # Validate structure before applying any updates
            temp_data = {
                "version": data.get("version", 1),
                "settings": deepcopy(current_settings),
                "last_modified": datetime.now(timezone.utc).isoformat(),
                "modified_by": modified_by,
            }

            for category, properties in patch.items():
                if category not in temp_data["settings"]:
                    temp_data["settings"][category] = {}
                temp_data["settings"][category].update(properties)

            self._validate_settings_structure(temp_data)

            # Apply validated updates to actual data
            for category, properties in patch.items():
                if category not in current_settings:
                    current_settings[category] = {}
                current_settings[category].update(properties)

            data["last_modified"] = temp_data["last_modified"]
            data["modified_by"] = modified_by

            self._save_atomic(data)
            return data

    def reset(self, modified_by: str = "system") -> None:
        """
        Clear all persisted settings; revert to defaults.

        Args:
            modified_by: Label for who triggered reset
        """
        with self._exclusive_lock():
            if self.path.exists():
                try:
                    self.path.unlink()
                except PermissionError as exc:
                    message = _permission_guidance(self.path, "resetting settings file")
                    logger.error(message)
                    raise SettingsValidationError(message) from exc
            logger.info("Settings reset to defaults by %s", modified_by)

    def get_changes_from_env(self, env_defaults: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get diff between current persisted settings and provided env defaults.
        Shows which settings have been overridden via the UI.

        Args:
            env_defaults: Dict matching schema structure with environment values

        Returns:
            Dict with 'overridden' list of {category, key, value, env_value} objects
        """
        current = self.load()
        overridden = []

        for category in ["camera", "logging", "discovery"]:
            persisted = current["settings"].get(category, {})
            env_vals = env_defaults.get(category, {})
            for key, value in persisted.items():
                if value is not None and value != env_vals.get(key):
                    overridden.append(
                        {
                            "category": category,
                            "key": key,
                            "value": value,
                            "env_value": env_vals.get(key),
                        }
                    )

        # Feature flags: show difference
        persisted_flags = current["settings"].get("feature_flags", {})
        if not isinstance(persisted_flags, dict):
            persisted_flags = {}

        env_flags = env_defaults.get("feature_flags", {})
        if not isinstance(env_flags, dict):
            env_flags = {}

        for flag_name, flag_value in persisted_flags.items():
            if flag_value != env_flags.get(flag_name):
                overridden.append(
                    {
                        "category": "feature_flags",
                        "key": flag_name,
                        "value": flag_value,
                        "env_value": env_flags.get(flag_name),
                    }
                )

        return {"overridden": overridden}

    @staticmethod
    def _clone_schema() -> Dict[str, Any]:
        """Create a copy of default schema."""
        return json.loads(json.dumps(ApplicationSettings.DEFAULT_SCHEMA))

    @staticmethod
    def _validate_settings_structure(data: Dict[str, Any]) -> None:
        """Validate settings structure before save."""
        if not isinstance(data, dict):
            raise SettingsValidationError(_ERROR_ROOT_NOT_DICT)

        if data.get("version") != 1:
            version = data.get("version")
            message = f"Unsupported schema version: {version}"
            raise SettingsValidationError(message)

        settings = data.get("settings", {})
        if not isinstance(settings, dict):
            raise SettingsValidationError(_ERROR_SETTINGS_NOT_DICT)

        # Check known categories exist
        for category in ["camera", "feature_flags", "logging", "discovery"]:
            if category not in settings:
                message = f"Missing required category: {category}"
                raise SettingsValidationError(message)

        category_error_messages = {
            "camera": _ERROR_CAMERA_NOT_DICT,
            "feature_flags": _ERROR_FEATURE_FLAGS_NOT_DICT,
            "logging": _ERROR_LOGGING_NOT_DICT,
            "discovery": _ERROR_DISCOVERY_NOT_DICT,
        }
        for category, error_message in category_error_messages.items():
            if not isinstance(settings[category], dict):
                raise SettingsValidationError(error_message)

    def _save_atomic(self, data: Dict[str, Any]) -> None:
        """Save data to file atomically using temp file + rename."""
        try:
            with tempfile.NamedTemporaryFile(
                "w", delete=False, dir=self.path.parent, encoding="utf-8", suffix=".tmp"
            ) as temp:
                json.dump(data, temp, indent=2)
                temp.flush()
                os.fsync(temp.fileno())
                temp_path = temp.name
            Path(temp_path).replace(self.path)
        except PermissionError as exc:
            message = _permission_guidance(self.path, "writing settings file")
            logger.error(message)
            raise SettingsValidationError(message) from exc

    @contextmanager
    def _exclusive_lock(self):
        """Context manager for exclusive file-based locking."""
        lock_path = self.path.parent / f"{self.path.name}.lock"
        try:
            with lock_path.open("a+b") as lock_file:
                if fcntl is not None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                    try:
                        yield
                    finally:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                    return

                if msvcrt is not None:
                    file_size = lock_file.seek(0, 2)
                    if file_size == 0:
                        lock_file.write(b"\0")
                        lock_file.flush()
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                    try:
                        yield
                    finally:
                        lock_file.seek(0)
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                    return

                message = "No supported file-lock backend available for this platform"
                raise RuntimeError(message)
        except PermissionError as exc:
            message = _permission_guidance(lock_path, "acquiring settings lock")
            logger.error(message)
            raise SettingsValidationError(message) from exc
