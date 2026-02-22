import logging
import os
import socket
from pathlib import Path
from typing import Any, Dict, Tuple

from .application_settings import ApplicationSettings, SettingsValidationError
from .feature_flags import is_flag_enabled


logger = logging.getLogger(__name__)

ALLOWED_APP_MODES = {"webcam", "management"}
DEFAULT_APP_MODE = "webcam"


def parse_resolution(resolution_str: str) -> Tuple[int, int]:
    """Parse resolution string into (width, height) tuple.

    Format: 'WIDTHxHEIGHT' (e.g., '640x480', '1920x1080').
    Valid ranges: 1-4096 pixels per dimension.

    Args:
        resolution_str: Resolution string in format 'WIDTHxHEIGHT'.

    Returns:
        Tuple of (width: int, height: int).

    Raises:
        ValueError: If format is invalid or dimensions are out of range.
    """
    parts = resolution_str.split("x")
    if len(parts) != 2:
        message = f"Invalid resolution format: {resolution_str}"
        raise ValueError(message)
    width, height = int(parts[0]), int(parts[1])
    if width <= 0 or height <= 0 or width > 4096 or height > 4096:
        message = f"Resolution dimensions out of valid range (1-4096): {width}x{height}"
        raise ValueError(message)
    return width, height


def _load_camera_config() -> Dict[str, Any]:
    """Load camera configuration from environment variables.

    Parses and validates camera settings with fallback defaults:
    - RESOLUTION (default: 640x480)
    - FPS (default: 24)
    - TARGET_FPS (default: matches FPS)
    - JPEG_QUALITY (1-100, default: 90)
    - MAX_FRAME_AGE_SECONDS (default: 10)
    - MAX_STREAM_CONNECTIONS (1-100, default: 10)

    Invalid values fall back to documented defaults without raising.

    Returns:
        Dict with keys: resolution (tuple), fps, target_fps, jpeg_quality,
        max_frame_age_seconds, max_stream_connections.
    """
    try:
        resolution = parse_resolution(os.environ.get("MIO_RESOLUTION", "640x480"))
    except ValueError:
        resolution = (640, 480)

    try:
        fps_raw = os.environ.get("MIO_FPS", "24")
        fps = int(fps_raw)
        if not 1 <= fps <= 120:
            logger.warning("Invalid MIO_FPS range '%s', using default 24", fps_raw)
            fps = 24
    except ValueError:
        logger.warning(
            "Invalid MIO_FPS value '%s', using default 24", os.environ.get("MIO_FPS", "24")
        )
        fps = 24

    try:
        target_fps = int(os.environ.get("MIO_TARGET_FPS", str(fps)))
    except ValueError:
        target_fps = fps

    try:
        jpeg_quality = int(os.environ.get("MIO_JPEG_QUALITY", "90"))
        if not 1 <= jpeg_quality <= 100:
            jpeg_quality = 90
    except ValueError:
        jpeg_quality = 90

    try:
        max_frame_age = float(os.environ.get("MIO_MAX_FRAME_AGE_SECONDS", "10"))
    except ValueError:
        max_frame_age = 10.0
    if max_frame_age <= 0:
        max_frame_age = 10.0

    try:
        max_stream_connections = int(os.environ.get("MIO_MAX_STREAM_CONNECTIONS", "10"))
    except ValueError:
        max_stream_connections = 10
    if not 1 <= max_stream_connections <= 100:
        max_stream_connections = 10

    return {
        "resolution": resolution,
        "fps": fps,
        "target_fps": target_fps,
        "jpeg_quality": jpeg_quality,
        "max_frame_age_seconds": max_frame_age,
        "max_stream_connections": max_stream_connections,
    }


def _apply_pi3_profile_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply Raspberry Pi 3 resource optimization defaults.

    When PI3_PROFILE=true and environment variables are NOT explicitly set,
    applies conservative defaults for Pi 3 limited resources:
    - Resolution: 640x480
    - FPS: 12
    - Target FPS: 12
    - JPEG Quality: 75
    - Max Connections: 3

    Skips any setting that was explicitly provided via environment variable.

    Args:
        config: Configuration dict from load_env_config().

    Returns:
        Config dict with Pi3 defaults applied where env vars weren't set.
    """
    if not config.get("pi3_profile_enabled", False):
        return config

    has_resolution = "MIO_RESOLUTION" in os.environ
    has_fps = "MIO_FPS" in os.environ
    has_target_fps = "MIO_TARGET_FPS" in os.environ
    has_jpeg_quality = "MIO_JPEG_QUALITY" in os.environ
    has_max_stream_connections = "MIO_MAX_STREAM_CONNECTIONS" in os.environ

    if not has_resolution:
        config["resolution"] = (640, 480)
    if not has_fps:
        config["fps"] = 12
    if not has_target_fps:
        config["target_fps"] = 12
    if not has_jpeg_quality:
        config["jpeg_quality"] = 75
    if not has_max_stream_connections:
        config["max_stream_connections"] = 3

    return config


def _load_stream_config() -> Dict[str, Any]:
    """Load stream and mock camera configuration from environment variables.

    Parses settings for API test mode and local mock camera feature flags.

    Env vars:
    - API_TEST_MODE_ENABLED (default: false)
    - API_TEST_CYCLE_INTERVAL_SECONDS (default: 5.0)

    Returns:
        Dict with keys: api_test_mode_enabled, api_test_cycle_interval_seconds.
    """
    api_test_mode_enabled = os.environ.get("MIO_API_TEST_MODE_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    try:
        api_test_cycle_interval_seconds = float(
            os.environ.get("MIO_API_TEST_CYCLE_INTERVAL_SECONDS", "5")
        )
    except ValueError:
        api_test_cycle_interval_seconds = 5.0
    if api_test_cycle_interval_seconds <= 0:
        api_test_cycle_interval_seconds = 5.0

    return {
        "api_test_mode_enabled": api_test_mode_enabled,
        "api_test_cycle_interval_seconds": api_test_cycle_interval_seconds,
    }


def _load_discovery_config() -> Dict[str, Any]:
    """Load webcam discovery/registration configuration from environment variables.

    Parses discovery protocol settings for webcam self-registration to management hub.

    Env vars:
    - DISCOVERY_ENABLED (default: false)
    - DISCOVERY_MANAGEMENT_URL (default: http://127.0.0.1:8001)
    - DISCOVERY_TOKEN (bearer token for announcement authentication)
    - DISCOVERY_INTERVAL_SECONDS (default: 30.0, minimum: >0)
    - DISCOVERY_WEBCAM_ID (optional, for identifying this node)

    Returns:
        Dict with keys: discovery_enabled, discovery_management_url, discovery_token,
        discovery_interval_seconds, discovery_webcam_id.
    """
    discovery_enabled = os.environ.get("MIO_DISCOVERY_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    discovery_management_url = os.environ.get(
        "MIO_DISCOVERY_MANAGEMENT_URL", "http://127.0.0.1:8001"
    )
    discovery_token = os.environ.get("MIO_DISCOVERY_TOKEN", "")
    try:
        discovery_interval_seconds = float(os.environ.get("MIO_DISCOVERY_INTERVAL_SECONDS", "30"))
    except ValueError:
        discovery_interval_seconds = 30.0
    if discovery_interval_seconds <= 0:
        discovery_interval_seconds = 30.0
    discovery_webcam_id = os.environ.get("MIO_DISCOVERY_WEBCAM_ID", "").strip()

    return {
        "discovery_enabled": discovery_enabled,
        "discovery_management_url": discovery_management_url,
        "discovery_token": discovery_token,
        "discovery_interval_seconds": discovery_interval_seconds,
        "discovery_webcam_id": discovery_webcam_id,
    }


def _load_logging_config() -> Dict[str, Any]:
    """Load logging configuration from environment variables.

    Env vars:
    - LOG_LEVEL: Python logging level (default: INFO)
    - LOG_FORMAT: text|json (default: text)
    - LOG_INCLUDE_IDENTIFIERS: true/false for process/thread IDs (default: false)

    Returns:
        Dict with keys: log_level, log_format, log_include_identifiers.
    """
    return {
        "log_level": os.environ.get("MIO_LOG_LEVEL", "INFO"),
        "log_format": os.environ.get("MIO_LOG_FORMAT", "text"),
        "log_include_identifiers": os.environ.get("MIO_LOG_INCLUDE_IDENTIFIERS", "false").lower()
        in (
            "1",
            "true",
            "yes",
        ),
    }


def _load_networking_config() -> Dict[str, Any]:
    """Load network binding and CORS configuration from environment variables.

    Env vars:
    - MIO_BIND_HOST (default: 127.0.0.1)
    - MIO_PORT (1-65535, default: 8000)
    - MIO_BASE_URL (default: http://hostname:8000)
    - CORS_SUPPORT (feature flag, default: false)
    - MIO_CORS_ORIGINS (default: * if enabled, else disabled)

    Returns:
        Dict with keys: cors_enabled, cors_origins, bind_host, bind_port, base_url.
    """
    cors_enabled = is_flag_enabled("CORS_SUPPORT")
    cors_origins_raw = os.environ.get("MIO_CORS_ORIGINS", "").strip()
    cors_origins = (cors_origins_raw or "*") if cors_enabled else "disabled"

    bind_host = os.environ.get("MIO_BIND_HOST", "127.0.0.1").strip()
    try:
        bind_port = int(os.environ.get("MIO_PORT", "8000"))
    except ValueError:
        bind_port = 8000
    if not 1 <= bind_port <= 65535:
        bind_port = 8000

    default_base_url = f"http://{socket.gethostname()}:8000"
    base_url = os.environ.get("MIO_BASE_URL", default_base_url).strip() or default_base_url

    return {
        "cors_enabled": cors_enabled,
        "cors_origins": cors_origins,
        "bind_host": bind_host,
        "bind_port": bind_port,
        "base_url": base_url,
    }


def _load_advanced_config() -> Dict[str, Any]:
    """Load advanced/internal configuration from environment variables.

    Env vars:
    - MIO_PI3_PROFILE or PI3_PROFILE (default: false)
    - MOCK_CAMERA (feature flag, default: false)
    - MIO_ALLOW_PYKMS_MOCK (default: false)
    - MIO_NODE_REGISTRY_PATH (default: /data/node-registry.json)
    - MIO_APPLICATION_SETTINGS_PATH (default: /data/application-settings.json)
    - MIO_MANAGEMENT_AUTH_TOKEN (bearer token for management mode auth)
    - MIO_WEBCAM_CONTROL_PLANE_AUTH_TOKEN (bearer token for webcam control-plane auth)
    - MIO_FAIL_ON_CAMERA_INIT_ERROR (default: false)

    Returns:
        Dict with keys: pi3_profile_enabled, mock_camera, allow_pykms_mock,
        webcam_registry_path, application_settings_path, management_auth_token,
        webcam_control_plane_auth_token, fail_on_camera_init_error.
    """
    pi3_profile_raw = os.environ.get("MIO_PI3_PROFILE", os.environ.get("PI3_PROFILE", "false"))

    fail_on_camera_init_error_raw = os.environ.get(
        "MIO_FAIL_ON_CAMERA_INIT_ERROR",
        "false",
    )

    return {
        "pi3_profile_enabled": pi3_profile_raw.lower() in ("1", "true", "yes"),
        "mock_camera": is_flag_enabled("MOCK_CAMERA"),
        "allow_pykms_mock": os.environ.get("MIO_ALLOW_PYKMS_MOCK", "false").lower()
        in ("1", "true", "yes"),
        "webcam_registry_path": os.environ.get(
            "MIO_NODE_REGISTRY_PATH", "/data/node-registry.json"
        ),
        "application_settings_path": os.environ.get(
            "MIO_APPLICATION_SETTINGS_PATH", "/data/application-settings.json"
        ),
        "management_auth_token": os.environ.get("MIO_MANAGEMENT_AUTH_TOKEN", ""),
        "webcam_control_plane_auth_token": os.environ.get(
            "MIO_WEBCAM_CONTROL_PLANE_AUTH_TOKEN", ""
        ),
        "fail_on_camera_init_error": fail_on_camera_init_error_raw.lower() in ("1", "true", "yes"),
    }


def load_env_config() -> Dict[str, Any]:
    """Load all configuration from environment variables.

    Assembles complete config by calling all _load_*_config() helpers.
    APP_MODE must be 'webcam' or 'management'.
    Applies Pi3 profile defaults if enabled.

    Env vars:
    - APP_MODE (default: webcam, required: must be 'webcam' or 'management')
    - All vars checked by _load_*_config() functions

    Returns:
        Complete flattened configuration dict with all keys from all
        _load_*_config() functions, plus pi3_profile_enabled flag.

    Raises:
        ValueError: If APP_MODE is invalid.
    """
    app_mode = os.environ.get("MIO_APP_MODE", DEFAULT_APP_MODE).strip().lower()
    if app_mode not in ALLOWED_APP_MODES:
        message = f"Invalid APP_MODE {app_mode}"
        raise ValueError(message)

    config = {"app_mode": app_mode}
    config.update(_load_camera_config())
    config.update(_load_stream_config())
    config.update(_load_discovery_config())
    config.update(_load_logging_config())
    config.update(_load_networking_config())
    config.update(_load_advanced_config())
    return _apply_pi3_profile_defaults(config)


def _merge_camera_settings(
    merged: Dict[str, Any], camera_settings: Dict[str, Any], env_config: Dict[str, Any]
) -> None:
    """Merge persisted camera settings into config.

    Validates and applies persisted settings for: resolution, fps, jpeg_quality,
    max_stream_connections, max_frame_age_seconds. Invalid values are logged
    and skipped (uses environment value instead). Modifies merged dict in-place.

    Args:
        merged: Config dict to update in-place (typically copy of env_config).
        camera_settings: Persisted camera settings from application_settings.json.
        env_config: Environment configuration for fallback values.
    """
    if camera_settings.get("resolution") is not None:
        resolution = camera_settings["resolution"]
        if isinstance(resolution, str):
            try:
                merged["resolution"] = parse_resolution(resolution)
            except ValueError:
                logger.warning("Invalid persisted resolution, using env value")
        else:
            logger.warning("Invalid persisted resolution type, using env value")

    if camera_settings.get("fps") is not None:
        fps = camera_settings["fps"]
        if isinstance(fps, int):
            if 0 <= fps <= 120:
                merged["fps"] = fps
                if merged.get("target_fps") == env_config.get("fps"):
                    merged["target_fps"] = fps
            else:
                logger.warning("Invalid persisted fps range, using env value")
        else:
            logger.warning("Invalid persisted fps type, using env value")

    if camera_settings.get("jpeg_quality") is not None:
        quality = camera_settings["jpeg_quality"]
        if isinstance(quality, int):
            if 1 <= quality <= 100:
                merged["jpeg_quality"] = quality
            else:
                logger.warning("Invalid persisted jpeg_quality range, using env value")
        else:
            logger.warning("Invalid persisted jpeg_quality type, using env value")

    if camera_settings.get("max_stream_connections") is not None:
        conns = camera_settings["max_stream_connections"]
        if isinstance(conns, int):
            if 1 <= conns <= 100:
                merged["max_stream_connections"] = conns
            else:
                logger.warning("Invalid persisted max_stream_connections range, using env value")
        else:
            logger.warning("Invalid persisted max_stream_connections type, using env value")

    if camera_settings.get("max_frame_age_seconds") is not None:
        age = camera_settings["max_frame_age_seconds"]
        if isinstance(age, (int, float)):
            if age > 0:
                merged["max_frame_age_seconds"] = age
            else:
                logger.warning("Invalid persisted max_frame_age_seconds range, using env value")
        else:
            logger.warning("Invalid persisted max_frame_age_seconds type, using env value")


def _merge_discovery_settings(merged: Dict[str, Any], discovery_settings: Dict[str, Any]) -> None:
    """Merge persisted discovery settings into config.

    Applies persisted settings for: discovery_enabled, discovery_management_url,
    discovery_token, discovery_interval_seconds. Validates values before merging.
    Modifies merged dict in-place.

    Args:
        merged: Config dict to update in-place (typically copy of env_config).
        discovery_settings: Persisted discovery settings from application_settings.json.
    """
    if discovery_settings.get("discovery_enabled") is not None:
        enabled = discovery_settings["discovery_enabled"]
        if isinstance(enabled, bool):
            merged["discovery_enabled"] = enabled
        else:
            logger.warning("Invalid persisted discovery_enabled type, using env value")
    if discovery_settings.get("discovery_management_url") is not None:
        url = discovery_settings["discovery_management_url"]
        if isinstance(url, str):
            if url.strip():
                merged["discovery_management_url"] = url
            else:
                logger.warning("Invalid persisted discovery_management_url value, using env value")
        else:
            logger.warning("Invalid persisted discovery_management_url type, using env value")
    if discovery_settings.get("discovery_token") is not None:
        token = discovery_settings["discovery_token"]
        if isinstance(token, str):
            merged["discovery_token"] = token
        else:
            logger.warning("Invalid persisted discovery_token type, using env value")
    if discovery_settings.get("discovery_interval_seconds") is not None:
        interval = discovery_settings["discovery_interval_seconds"]
        if isinstance(interval, (int, float)):
            if interval > 0:
                merged["discovery_interval_seconds"] = interval
            else:
                logger.warning(
                    "Invalid persisted discovery_interval_seconds range, using env value"
                )
        else:
            logger.warning("Invalid persisted discovery_interval_seconds type, using env value")


def _merge_logging_settings(merged: Dict[str, Any], logging_settings: Dict[str, Any]) -> None:
    """Merge persisted logging settings into config.

    Applies persisted settings for: log_level, log_format, log_include_identifiers.
    Modifies merged dict in-place.

    Args:
        merged: Config dict to update in-place (typically copy of env_config).
        logging_settings: Persisted logging settings from application_settings.json.
    """
    if logging_settings.get("log_level") is not None:
        level = logging_settings["log_level"]
        if isinstance(level, str):
            merged["log_level"] = level
        else:
            logger.warning("Invalid persisted log_level type, using env value")
    if logging_settings.get("log_format") is not None:
        log_format = logging_settings["log_format"]
        if isinstance(log_format, str):
            merged["log_format"] = log_format
        else:
            logger.warning("Invalid persisted log_format type, using env value")
    if logging_settings.get("log_include_identifiers") is not None:
        include_identifiers = logging_settings["log_include_identifiers"]
        if isinstance(include_identifiers, bool):
            merged["log_include_identifiers"] = include_identifiers
        else:
            logger.warning("Invalid persisted log_include_identifiers type, using env value")


def merge_config_with_persisted_settings(
    env_config: Dict[str, Any], persisted: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge persisted application settings with environment configuration.

    Precedence (high to low):
    1. Persisted settings from application_settings.json (if valid)
    2. Environment variables (fallback)

    Args:
        env_config: Full environment configuration from load_env_config().
        persisted: Parsed JSON from ApplicationSettings.load() (or dict like {}).

    Returns:
        Merged config dict with persisted settings overriding env values where present.
    """
    merged = dict(env_config)
    settings = persisted.get("settings", {}) if isinstance(persisted, dict) else {}
    _merge_camera_settings(merged, settings.get("camera", {}), env_config)
    _merge_discovery_settings(merged, settings.get("discovery", {}))
    _merge_logging_settings(merged, settings.get("logging", {}))
    return merged


def merge_config_with_settings(
    env_config: Dict[str, Any], app_settings: ApplicationSettings | None = None
) -> Dict[str, Any]:
    """Load and merge persisted settings with environment configuration.

    Attempts to load persisted settings from file. If loading fails (validation error,
    file not found, parse error), logs warning and returns env_config unchanged.
    Merging uses merge_config_with_persisted_settings().

    Args:
        env_config: Full environment configuration from load_env_config().
        app_settings: Optional ApplicationSettings instance; creates new if None.

    Returns:
        Merged configuration, or env_config if persisted settings unavailable.
    """
    try:
        settings_store = app_settings or ApplicationSettings(
            env_config.get("application_settings_path", "/data/application-settings.json")
        )
        persisted = settings_store.load()
        return merge_config_with_persisted_settings(env_config, persisted)
    except SettingsValidationError as exc:
        logger.warning("Could not load persisted settings: %s. Using env config only.", exc)
    except Exception as exc:
        logger.warning(
            "Unexpected error loading persisted settings: %s. Using env config only.", exc
        )
    return dict(env_config)


def get_effective_settings_payload(app_settings: ApplicationSettings) -> Dict[str, Any]:
    """Get current effective settings as JSON-serializable payload.

    Loads environment config, merges with persisted settings, and returns
    structured payload for /api/settings endpoint. Includes source metadata,
    timestamps, and feature flags from persisted store.

    Args:
        app_settings: ApplicationSettings instance for loading persisted data.

    Returns:
        Dict with keys: source, settings (camera/logging/discovery/feature_flags),
        last_modified, modified_by.
    """
    env_config = load_env_config()
    try:
        persisted = app_settings.load()
    except SettingsValidationError as exc:
        logger.warning("Could not load persisted settings: %s. Using env config only.", exc)
        persisted = {}
    except Exception as exc:
        logger.warning(
            "Unexpected error loading persisted settings: %s. Using env config only.", exc
        )
        persisted = {}

    merged = merge_config_with_persisted_settings(env_config, persisted)

    return {
        "source": "merged",
        "settings": {
            "camera": {
                "resolution": f"{merged['resolution'][0]}x{merged['resolution'][1]}",
                "fps": merged["fps"],
                "jpeg_quality": merged["jpeg_quality"],
                "max_stream_connections": merged["max_stream_connections"],
                "max_frame_age_seconds": merged["max_frame_age_seconds"],
            },
            "logging": {
                "log_level": merged["log_level"],
                "log_format": merged["log_format"],
                "log_include_identifiers": merged["log_include_identifiers"],
            },
            "discovery": {
                "discovery_enabled": merged["discovery_enabled"],
                "discovery_management_url": merged["discovery_management_url"],
                "discovery_token": merged["discovery_token"],
                "discovery_interval_seconds": merged["discovery_interval_seconds"],
            },
            "feature_flags": persisted.get("settings", {}).get("feature_flags", {}),
        },
        "last_modified": persisted.get("last_modified"),
        "modified_by": persisted.get("modified_by"),
    }


def load_build_metadata() -> Dict[str, str]:
    """Load build-time metadata from /app/BUILD_METADATA file.

    Reads key-value pairs created at build time documenting:
    - DEBIAN_SUITE: Debian release (e.g., trixie, bookworm)
    - RPI_SUITE: Raspberry Pi repo suite
    - BUILD_TIMESTAMP: ISO-8601 timestamp of build completion

    Returns:
        Dictionary of build metadata. Returns empty dict if file not found
        or unreadable (e.g., in development without Docker).

    Example:
        >>> metadata = load_build_metadata()
        >>> metadata.get("DEBIAN_SUITE")
        "trixie"
    """
    metadata: Dict[str, str] = {}
    metadata_file = "/app/BUILD_METADATA"

    if not Path(metadata_file).exists():
        logger.debug("BUILD_METADATA file not found at %s (normal in dev)", metadata_file)
        return metadata

    try:
        with Path(metadata_file).open(encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if line and "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    metadata[key.strip()] = value.strip()
        logger.debug("Loaded BUILD_METADATA: %s", metadata)
    except Exception as e:
        logger.warning("Failed to read BUILD_METADATA: %s", e)

    return metadata
