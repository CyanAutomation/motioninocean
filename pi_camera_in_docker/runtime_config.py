import logging
import os
from typing import Any, Dict, Tuple

from .application_settings import ApplicationSettings, SettingsValidationError
from .feature_flags import is_flag_enabled

logger = logging.getLogger(__name__)

ALLOWED_APP_MODES = {"webcam", "management"}
DEFAULT_APP_MODE = "webcam"


def parse_resolution(resolution_str: str) -> Tuple[int, int]:
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
    try:
        resolution = parse_resolution(os.environ.get("RESOLUTION", "640x480"))
    except ValueError:
        resolution = (640, 480)

    try:
        fps = int(os.environ.get("FPS", "0"))
    except ValueError:
        fps = 0

    try:
        target_fps = int(os.environ.get("TARGET_FPS", str(fps)))
    except ValueError:
        target_fps = fps

    try:
        jpeg_quality = int(os.environ.get("JPEG_QUALITY", "90"))
        if not 1 <= jpeg_quality <= 100:
            jpeg_quality = 90
    except ValueError:
        jpeg_quality = 90

    try:
        max_frame_age = float(os.environ.get("MAX_FRAME_AGE_SECONDS", "10"))
    except ValueError:
        max_frame_age = 10.0
    if max_frame_age <= 0:
        max_frame_age = 10.0

    try:
        max_stream_connections = int(os.environ.get("MAX_STREAM_CONNECTIONS", "10"))
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
    if not config.get("pi3_profile_enabled", False):
        return config

    has_resolution = "RESOLUTION" in os.environ
    has_fps = "FPS" in os.environ
    has_target_fps = "TARGET_FPS" in os.environ
    has_jpeg_quality = "JPEG_QUALITY" in os.environ
    has_max_stream_connections = "MAX_STREAM_CONNECTIONS" in os.environ

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
    api_test_mode_enabled = os.environ.get("API_TEST_MODE_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    try:
        api_test_cycle_interval_seconds = float(
            os.environ.get("API_TEST_CYCLE_INTERVAL_SECONDS", "5")
        )
    except ValueError:
        api_test_cycle_interval_seconds = 5.0
    if api_test_cycle_interval_seconds <= 0:
        api_test_cycle_interval_seconds = 5.0

    cat_gif_enabled = is_flag_enabled("CAT_GIF")
    cataas_api_url = os.environ.get("CATAAS_API_URL", "https://cataas.com/cat.gif").strip()
    try:
        cat_gif_cache_ttl_seconds = float(os.environ.get("CAT_GIF_CACHE_TTL_SECONDS", "60"))
    except ValueError:
        cat_gif_cache_ttl_seconds = 60.0
    if cat_gif_cache_ttl_seconds <= 0:
        cat_gif_cache_ttl_seconds = 60.0

    return {
        "api_test_mode_enabled": api_test_mode_enabled,
        "api_test_cycle_interval_seconds": api_test_cycle_interval_seconds,
        "cat_gif_enabled": cat_gif_enabled,
        "cataas_api_url": cataas_api_url,
        "cat_gif_cache_ttl_seconds": cat_gif_cache_ttl_seconds,
    }


def _load_discovery_config() -> Dict[str, Any]:
    discovery_enabled = os.environ.get("DISCOVERY_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    discovery_management_url = os.environ.get("DISCOVERY_MANAGEMENT_URL", "http://127.0.0.1:8001")
    discovery_token = os.environ.get("DISCOVERY_TOKEN", "")
    try:
        discovery_interval_seconds = float(os.environ.get("DISCOVERY_INTERVAL_SECONDS", "30"))
    except ValueError:
        discovery_interval_seconds = 30.0
    if discovery_interval_seconds <= 0:
        discovery_interval_seconds = 30.0
    discovery_node_id = os.environ.get("DISCOVERY_NODE_ID", "").strip()

    return {
        "discovery_enabled": discovery_enabled,
        "discovery_management_url": discovery_management_url,
        "discovery_token": discovery_token,
        "discovery_interval_seconds": discovery_interval_seconds,
        "discovery_node_id": discovery_node_id,
    }


def _load_logging_config() -> Dict[str, Any]:
    return {
        "log_level": os.environ.get("LOG_LEVEL", "INFO"),
        "log_format": os.environ.get("LOG_FORMAT", "text"),
        "log_include_identifiers": os.environ.get("LOG_INCLUDE_IDENTIFIERS", "false").lower() in (
            "1",
            "true",
            "yes",
        ),
    }


def _load_networking_config() -> Dict[str, Any]:
    cors_enabled = is_flag_enabled("CORS_SUPPORT")
    cors_origins_raw = os.environ.get("MOTION_IN_OCEAN_CORS_ORIGINS", "").strip()
    cors_origins = cors_origins_raw or "*" if cors_enabled else "disabled"

    bind_host = os.environ.get("MOTION_IN_OCEAN_BIND_HOST", "127.0.0.1").strip()
    try:
        bind_port = int(os.environ.get("MOTION_IN_OCEAN_PORT", "8000"))
    except ValueError:
        bind_port = 8000
    if not 1 <= bind_port <= 65535:
        bind_port = 8000

    return {
        "cors_enabled": cors_enabled,
        "cors_origins": cors_origins,
        "bind_host": bind_host,
        "bind_port": bind_port,
    }


def _load_advanced_config() -> Dict[str, Any]:
    pi3_profile_raw = os.environ.get(
        "MOTION_IN_OCEAN_PI3_PROFILE", os.environ.get("PI3_PROFILE", "false")
    )

    return {
        "pi3_profile_enabled": pi3_profile_raw.lower() in ("1", "true", "yes"),
        "mock_camera": is_flag_enabled("MOCK_CAMERA"),
        "allow_pykms_mock": os.environ.get("ALLOW_PYKMS_MOCK", "false").lower()
        in ("1", "true", "yes"),
        "node_registry_path": os.environ.get("NODE_REGISTRY_PATH", "/data/node-registry.json"),
        "management_auth_token": os.environ.get("MANAGEMENT_AUTH_TOKEN", ""),
    }


def load_env_config() -> Dict[str, Any]:
    app_mode = os.environ.get("APP_MODE", DEFAULT_APP_MODE).strip().lower()
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


def _merge_camera_settings(merged: Dict[str, Any], camera_settings: Dict[str, Any], env_config: Dict[str, Any]) -> None:
    if camera_settings.get("resolution") is not None:
        try:
            merged["resolution"] = parse_resolution(camera_settings["resolution"])
        except ValueError:
            logger.warning("Invalid persisted resolution, using env value")

    if camera_settings.get("fps") is not None:
        merged["fps"] = camera_settings["fps"]
        if merged.get("target_fps") == env_config.get("fps"):
            merged["target_fps"] = camera_settings["fps"]

    if camera_settings.get("jpeg_quality") is not None:
        quality = camera_settings["jpeg_quality"]
        if 1 <= quality <= 100:
            merged["jpeg_quality"] = quality

    if camera_settings.get("max_stream_connections") is not None:
        conns = camera_settings["max_stream_connections"]
        if 1 <= conns <= 100:
            merged["max_stream_connections"] = conns

    if camera_settings.get("max_frame_age_seconds") is not None:
        age = camera_settings["max_frame_age_seconds"]
        if age > 0:
            merged["max_frame_age_seconds"] = age


def _merge_discovery_settings(merged: Dict[str, Any], discovery_settings: Dict[str, Any]) -> None:
    if discovery_settings.get("discovery_enabled") is not None:
        merged["discovery_enabled"] = discovery_settings["discovery_enabled"]
    if discovery_settings.get("discovery_management_url") is not None:
        url = discovery_settings["discovery_management_url"]
        if url.strip():
            merged["discovery_management_url"] = url
    if discovery_settings.get("discovery_token") is not None:
        merged["discovery_token"] = discovery_settings["discovery_token"]
    if discovery_settings.get("discovery_interval_seconds") is not None:
        interval = discovery_settings["discovery_interval_seconds"]
        if interval > 0:
            merged["discovery_interval_seconds"] = interval


def _merge_logging_settings(merged: Dict[str, Any], logging_settings: Dict[str, Any]) -> None:
    if logging_settings.get("log_level") is not None:
        merged["log_level"] = logging_settings["log_level"]
    if logging_settings.get("log_format") is not None:
        merged["log_format"] = logging_settings["log_format"]
    if logging_settings.get("log_include_identifiers") is not None:
        merged["log_include_identifiers"] = logging_settings["log_include_identifiers"]


def merge_config_with_settings(env_config: Dict[str, Any], app_settings: ApplicationSettings | None = None) -> Dict[str, Any]:
    merged = dict(env_config)
    try:
        settings_store = app_settings or ApplicationSettings()
        persisted = settings_store.load()
        settings = persisted.get("settings", {})
        _merge_camera_settings(merged, settings.get("camera", {}), env_config)
        _merge_discovery_settings(merged, settings.get("discovery", {}))
        _merge_logging_settings(merged, settings.get("logging", {}))
    except SettingsValidationError as exc:
        logger.warning(f"Could not load persisted settings: {exc}. Using env config only.")
    except Exception as exc:
        logger.warning(f"Unexpected error loading persisted settings: {exc}. Using env config only.")
    return merged


def get_effective_settings_payload(app_settings: ApplicationSettings) -> Dict[str, Any]:
    env_config = load_env_config()
    merged = merge_config_with_settings(env_config, app_settings=app_settings)
    persisted = app_settings.load()
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
