"""Feature flag system for Motion in Ocean.

This module provides a centralized feature flag registry. Feature flags enable
gradual rollouts, experimental features, performance optimizations, and A/B testing.
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional


logger = logging.getLogger(__name__)


ACTIVE_RUNTIME_FLAGS = (
    "MOCK_CAMERA",
    "OCTOPRINT_COMPATIBILITY",
)
"""Feature flags that currently have concrete runtime reads in production code."""


class FeatureFlagCategory(Enum):
    """Categorization for feature flags."""

    PERFORMANCE = "Performance"
    EXPERIMENTAL = "Experimental"
    HARDWARE_OPTIMIZATION = "Hardware Optimization"
    DEVELOPER_TOOLS = "Developer Tools"
    INTEGRATION_COMPATIBILITY = "Integration Compatibility"
    GRADUAL_ROLLOUT = "Gradual Rollout"
    OBSERVABILITY = "Observability"


@dataclass
class FeatureFlag:
    """Represents a single feature flag with metadata."""

    name: str
    """The flag name (without MIO_ prefix)."""

    default: bool
    """Default value if not set in environment."""

    category: FeatureFlagCategory
    """Category for organizing related flags."""

    description: str
    """Human-readable description of the flag's purpose."""

    backward_compat_vars: Optional[list[str]] = None
    """List of legacy environment variable names that map to this flag."""

    validator: Optional[Callable[[str], bool]] = None
    """Optional custom validator function for parsing string values."""

    enabled: bool = False
    """Current enabled state (populated at initialization)."""


class FeatureFlags:
    """Registry and manager for all feature flags."""

    def __init__(self) -> None:
        """Initialize the feature flag registry."""
        self._flags: Dict[str, FeatureFlag] = {}
        self._loaded = False
        self._define_flags()

    def _define_flags(self) -> None:
        """Define all available feature flags with active runtime integrations only."""
        self.register(
            FeatureFlag(
                name="MOCK_CAMERA",
                default=False,
                category=FeatureFlagCategory.EXPERIMENTAL,
                description="Use mock camera for testing without real hardware.",
            )
        )

        self.register(
            FeatureFlag(
                name="OCTOPRINT_COMPATIBILITY",
                default=False,
                category=FeatureFlagCategory.INTEGRATION_COMPATIBILITY,
                description="Enable OctoPrint camera format compatibility mode.",
            )
        )

    def register(self, flag: FeatureFlag) -> None:
        """Register a feature flag.

        Args:
            flag: FeatureFlag instance to register.

        Raises:
            ValueError: If flag name already exists or is invalid.
        """
        if flag.name in self._flags:
            message = f"Feature flag '{flag.name}' already registered"
            raise ValueError(message)

        if not flag.name:
            message = "Feature flag name cannot be empty"
            raise ValueError(message)

        self._flags[flag.name] = flag

    def load(self) -> None:
        """Load all feature flags from environment variables."""
        if self._loaded:
            logger.warning("Feature flags already loaded, skipping reload")
            return

        for flag_name, flag in self._flags.items():
            # Try MIO_ prefixed name first
            env_var = f"MIO_{flag_name}"
            value = os.environ.get(env_var)

            # Parse the value
            if value is not None:
                flag.enabled = self._parse_bool(value, flag.name)
                logger.debug("Feature flag '%s' = %s (from environment)", flag_name, flag.enabled)
            else:
                flag.enabled = flag.default
                logger.debug("Feature flag '%s' = %s (default)", flag_name, flag.enabled)

        self._loaded = True
        self._log_summary()

    def _parse_bool(self, value: str, flag_name: str) -> bool:
        """Parse a string value as boolean.

        Args:
            value: String value to parse.
            flag_name: Name of flag (for logging).

        Returns:
            Boolean value.
        """
        value_lower = value.lower().strip()
        if value_lower in ("true", "1", "t", "yes", "on"):
            return True
        if value_lower in ("false", "0", "f", "no", "off"):
            return False
        logger.warning(
            "Invalid boolean value '%s' for feature flag '%s'. "
            "Valid values: true, 1, t, yes, on, false, 0, f, no, off. "
            "Using default %s",
            value,
            flag_name,
            self._flags[flag_name].default,
        )
        return self._flags[flag_name].default

    def is_enabled(self, flag_name: str) -> bool:
        """Check if a feature flag is enabled.

        Args:
            flag_name: Name of the flag to check.

        Returns:
            True if enabled, False otherwise.

        Raises:
            KeyError: If flag not found.
        """
        if flag_name not in self._flags:
            message = f"Unknown feature flag: {flag_name}"
            raise KeyError(message)

        return self._flags[flag_name].enabled

    def get_all_flags(self) -> Dict[str, bool]:
        """Get a dictionary of all flags and their current state.

        Returns:
            Dict mapping flag names to boolean enabled states.
        """
        return {name: flag.enabled for name, flag in self._flags.items()}

    def get_flags_by_category(self, category: FeatureFlagCategory) -> Dict[str, bool]:
        """Get all flags in a specific category.

        Args:
            category: FeatureFlagCategory to filter by.

        Returns:
            Dict of flag names to enabled states for that category.
        """
        return {
            name: flag.enabled for name, flag in self._flags.items() if flag.category == category
        }

    def get_flag_info(self, flag_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a flag.

        Args:
            flag_name: Name of the flag.

        Returns:
            Dict with flag metadata, or None if not found.
        """
        if flag_name not in self._flags:
            return None

        flag = self._flags[flag_name]
        return {
            "name": flag.name,
            "enabled": flag.enabled,
            "default": flag.default,
            "category": flag.category.value,
            "description": flag.description,
            "backward_compat_vars": flag.backward_compat_vars or [],
        }

    def get_all_flag_info(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed metadata for all registered flags.

        Returns:
            Dict mapping flag names to metadata dictionaries.
        """
        return {
            flag_name: flag_info
            for flag_name in self._flags
            if (flag_info := self.get_flag_info(flag_name)) is not None
        }

    def _log_summary(self) -> None:
        """Log a summary of loaded feature flags grouped by category."""
        if not self._loaded:
            return

        non_default = sorted(
            name for name, flag in self._flags.items() if flag.enabled != flag.default
        )
        non_default_str = ", ".join(non_default) if non_default else "none"
        logger.info(
            "Feature Flags Loaded: total=%d non_default=%s (set MIO_LOG_LEVEL=DEBUG for full listing)",
            len(self._flags),
            non_default_str,
        )
        for category in FeatureFlagCategory:
            flags_in_category = self.get_flags_by_category(category)
            if flags_in_category:
                enabled_count = sum(1 for v in flags_in_category.values() if v)
                status = " | ".join(
                    f"{name}={enabled}" for name, enabled in sorted(flags_in_category.items())
                )
                logger.debug(
                    "  %s: (%s/%s enabled) | %s",
                    category.value,
                    enabled_count,
                    len(flags_in_category),
                    status,
                )

    def get_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of all feature flags.

        Returns:
            Dict with flags organized by category.
        """
        summary: Dict[str, Any] = {}
        for category in FeatureFlagCategory:
            summary[category.value] = self.get_flags_by_category(category)
        return summary


# Global instance
_feature_flags: FeatureFlags = FeatureFlags()


def get_feature_flags() -> FeatureFlags:
    """Get the global feature flags instance.

    Returns:
        FeatureFlags instance.
    """
    return _feature_flags


def is_flag_enabled(flag_name: str) -> bool:
    """Convenience function to check if a flag is enabled.

    Args:
        flag_name: Name of the flag.

    Returns:
        True if enabled, False otherwise.

    Raises:
        KeyError: If flag not found.
    """
    return get_feature_flags().is_enabled(flag_name)
