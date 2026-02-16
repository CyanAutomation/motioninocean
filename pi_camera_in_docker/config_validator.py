"""Configuration validation and startup checks."""

from typing import Any, Dict, Optional

from .settings_schema import SettingsSchema


class ConfigValidationError(ValueError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(message)
        self.hint = hint


def validate_discovery_config(config: Dict[str, Any]) -> None:
    """Validate cross-field discovery configuration.

    Args:
        config: Configuration dictionary

    Raises:
        ConfigValidationError: If discovery config is invalid
    """
    if not config.get("discovery_enabled"):
        return  # Validation only needed if discovery is enabled

    # If discovery is enabled, require management URL and token
    management_url = config.get("discovery_management_url", "").strip()
    token = config.get("discovery_token", "").strip()
    base_url = config.get("base_url", "").strip()

    if not management_url:
        message = "DISCOVERY_ENABLED=true requires DISCOVERY_MANAGEMENT_URL to be set"
        raise ConfigValidationError(
            message,
            hint="Example: DISCOVERY_MANAGEMENT_URL=http://management-host:8001",
        )

    if not token:
        message = "DISCOVERY_ENABLED=true requires DISCOVERY_TOKEN to be set"
        raise ConfigValidationError(
            message,
            hint="Use same token as NODE_DISCOVERY_SHARED_SECRET on management node",
        )

    if not base_url or base_url == "http://unknown-host:8000":
        message = "DISCOVERY_ENABLED=true requires BASE_URL to be set to reachable address"
        raise ConfigValidationError(
            message,
            hint="Example: BASE_URL=http://192.168.1.100:8000",
        )


def validate_all_config(config: Dict[str, Any]) -> None:
    """Validate complete configuration at startup.

    Args:
        config: Configuration dictionary returned from _load_config()

    Raises:
        ConfigValidationError: If any configuration is invalid
    """
    # Validate discovery configuration if enabled
    validate_discovery_config(config)

    # Future: Add more cross-field validations here
    # For example:
    # - If TARGET_FPS set, ensure it's not higher than FPS
    # - If MANAGEMENT_AUTH_TOKEN set, ensure it's strong enough
    # etc.


def validate_settings_patch(patch: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate a settings PATCH request.

    Args:
        patch: Dict with structure { category: { property: value } }

    Returns:
        Dict of error messages { "category.property": "error message" } (empty if valid)
    """
    errors = {}

    if not isinstance(patch, dict):
        return {"_root": "Patch must be a dictionary"}

    # Iterate through all categories and properties in patch
    for category, properties in patch.items():
        if not isinstance(properties, dict):
            errors[f"{category}"] = "Category must contain property objects"
            continue

        for prop_name, value in properties.items():
            is_valid, error_msg = SettingsSchema.validate_value(category, prop_name, value)
            if not is_valid:
                errors[f"{category}.{prop_name}"] = error_msg

    return errors
