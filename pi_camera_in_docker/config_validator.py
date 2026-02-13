"""Configuration validation and startup checks."""

import os
import re
from typing import Any, Dict, Optional, Tuple


class ConfigValidationError(ValueError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(message)
        self.hint = hint


def validate_resolution(value: str) -> Tuple[int, int]:
    """Validate and parse RESOLUTION environment variable.
    
    Args:
        value: Expected format: WIDTHxHEIGHT (e.g., "640x480")
        
    Returns:
        Tuple of (width, height)
        
    Raises:
        ConfigValidationError: If format invalid or values out of range
    """
    if not value or not isinstance(value, str):
        raise ConfigValidationError(
            "RESOLUTION must be a non-empty string",
            hint="Expected format: WIDTHxHEIGHT (e.g., 640x480)",
        )

    parts = value.split("x")
    if len(parts) != 2:
        raise ConfigValidationError(
            f"RESOLUTION format invalid: '{value}'",
            hint="Expected format: WIDTHxHEIGHT (e.g., 640x480)",
        )

    try:
        width, height = int(parts[0].strip()), int(parts[1].strip())
    except ValueError:
        raise ConfigValidationError(
            f"RESOLUTION values must be integers: '{value}'",
            hint="Expected format: WIDTHxHEIGHT (e.g., 640x480)",
        )

    if not (1 <= width <= 4096) or not (1 <= height <= 4096):
        raise ConfigValidationError(
            f"RESOLUTION values out of range: width={width}, height={height}",
            hint="Both width and height must be between 1 and 4096 pixels",
        )

    return (width, height)


def validate_integer_range(
    value: Optional[str],
    name: str,
    min_val: int,
    max_val: int,
    default: int,
) -> int:
    """Validate integer config parameter with range check.
    
    Args:
        value: String value to parse
        name: Config parameter name (for error messages)
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        default: Default value if not provided or invalid
        
    Returns:
        Validated integer value
        
    Raises:
        ConfigValidationError: If value out of range
    """
    if value is None or value.strip() == "":
        return default

    try:
        parsed = int(value.strip())
    except ValueError:
        raise ConfigValidationError(
            f"{name} must be an integer, got: '{value}'",
            hint=f"Valid range: {min_val}-{max_val}",
        )

    if not (min_val <= parsed <= max_val):
        raise ConfigValidationError(
            f"{name} value out of range: {parsed}",
            hint=f"Valid range: {min_val}-{max_val}",
        )

    return parsed


def validate_float_range(
    value: Optional[str],
    name: str,
    min_val: float,
    max_val: float,
    default: float,
) -> float:
    """Validate float config parameter with range check.
    
    Args:
        value: String value to parse
        name: Config parameter name (for error messages)
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        default: Default value if not provided or invalid
        
    Returns:
        Validated float value
        
    Raises:
        ConfigValidationError: If value out of range
    """
    if value is None or value.strip() == "":
        return default

    try:
        parsed = float(value.strip())
    except ValueError:
        raise ConfigValidationError(
            f"{name} must be a float, got: '{value}'",
            hint=f"Valid range: {min_val}-{max_val}",
        )

    if not (min_val <= parsed <= max_val):
        raise ConfigValidationError(
            f"{name} value out of range: {parsed}",
            hint=f"Valid range: {min_val}-{max_val}",
        )

    return parsed


def validate_app_mode(value: str) -> str:
    """Validate APP_MODE environment variable.
    
    Args:
        value: App mode value
        
    Returns:
        Validated app mode
        
    Raises:
        ConfigValidationError: If not a valid app mode
    """
    allowed = {"webcam", "management"}
    if value.strip().lower() not in allowed:
        raise ConfigValidationError(
            f"APP_MODE must be one of {allowed}, got: '{value}'",
            hint=f"Set APP_MODE={next(iter(allowed))} or equivalent",
        )
    return value.strip().lower()


def validate_url(value: str, name: str, allow_localhost: bool = True) -> str:
    """Validate URL format.
    
    Args:
        value: URL to validate
        name: Parameter name (for error messages)
        allow_localhost: Whether to allow localhost URLs
        
    Returns:
        Validated URL
        
    Raises:
        ConfigValidationError: If URL format invalid
    """
    if not value or not value.strip():
        raise ConfigValidationError(
            f"{name} cannot be empty",
            hint="Expected format: http://host:port or http://ip:port",
        )

    url = value.strip()

    if not url.startswith(("http://", "https://")):
        raise ConfigValidationError(
            f"{name} must start with http:// or https://, got: '{url}'",
            hint="Example: http://192.168.1.100:8001",
        )

    # Basic URL pattern check
    pattern = r"^https?://[a-zA-Z0-9\.\-]+(:[0-9]+)?(/.*)?$"
    if not re.match(pattern, url):
        raise ConfigValidationError(
            f"{name} format invalid: '{url}'",
            hint="Expected format: http://host:port or http://ip:port",
        )

    return url


def validate_bearer_token(value: str, name: str) -> str:
    """Validate bearer token format.
    
    Args:
        value: Token value
        name: Parameter name (for error messages)
        
    Returns:
        Validated token
        
    Raises:
        ConfigValidationError: If token invalid
    """
    if value and len(value.strip()) < 8:
        raise ConfigValidationError(
            f"{name} is too short (minimum 8 characters): {len(value)} chars",
            hint="Use a strong random token, e.g., from: openssl rand -hex 16",
        )

    return value.strip() if value else ""


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
        raise ConfigValidationError(
            "DISCOVERY_ENABLED=true requires DISCOVERY_MANAGEMENT_URL to be set",
            hint="Example: DISCOVERY_MANAGEMENT_URL=http://management-host:8001",
        )

    if not token:
        raise ConfigValidationError(
            "DISCOVERY_ENABLED=true requires DISCOVERY_TOKEN to be set",
            hint="Use same token as NODE_DISCOVERY_SHARED_SECRET on management node",
        )

    if not base_url or base_url == "http://unknown-host:8000":
        raise ConfigValidationError(
            "DISCOVERY_ENABLED=true requires BASE_URL to be set to reachable address",
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
