"""Feature flag system for Motion in Ocean.

This module provides a centralized feature flag registry with automatic backward
compatibility for existing environment variables. Feature flags enable gradual
rollouts, experimental features, performance optimizations, and A/B testing.
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set

logger = logging.getLogger(__name__)


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
    """The flag name (without MOTION_IN_OCEAN_ prefix)."""
    
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
        self._legacy_mappings: Dict[str, str] = {}  # Maps legacy var names to flag names
        self._define_flags()

    def _define_flags(self) -> None:
        """Define all available feature flags."""
        # PERFORMANCE FLAGS
        self.register(
            FeatureFlag(
                name="QUALITY_ADAPTATION",
                default=False,
                category=FeatureFlagCategory.PERFORMANCE,
                description="Enable automatic JPEG quality adaptation based on network conditions.",
                backward_compat_vars=None,
            )
        )

        self.register(
            FeatureFlag(
                name="FPS_THROTTLE_ADAPTIVE",
                default=False,
                category=FeatureFlagCategory.PERFORMANCE,
                description="Enable adaptive FPS throttling based on client capabilities.",
                backward_compat_vars=None,
            )
        )

        self.register(
            FeatureFlag(
                name="FRAME_SIZE_OPTIMIZATION",
                default=True,
                category=FeatureFlagCategory.PERFORMANCE,
                description="Enable frame size optimization for bandwidth-constrained networks.",
                backward_compat_vars=None,
            )
        )

        # OPTIONAL FEATURES
        self.register(
            FeatureFlag(
                name="MOCK_CAMERA",
                default=False,
                category=FeatureFlagCategory.EXPERIMENTAL,
                description="Use mock camera for testing without real hardware.",
                backward_compat_vars=["MOCK_CAMERA"],
            )
        )

        self.register(
            FeatureFlag(
                name="MOTION_DETECTION",
                default=False,
                category=FeatureFlagCategory.EXPERIMENTAL,
                description="Enable motion detection hooks for frame analysis.",
                backward_compat_vars=None,
            )
        )

        self.register(
            FeatureFlag(
                name="FRAME_RECORDING",
                default=False,
                category=FeatureFlagCategory.EXPERIMENTAL,
                description="Enable frame recording/buffering to disk.",
                backward_compat_vars=None,
            )
        )

        # HARDWARE OPTIMIZATION FLAGS
        self.register(
            FeatureFlag(
                name="PI3_OPTIMIZATION",
                default=False,
                category=FeatureFlagCategory.HARDWARE_OPTIMIZATION,
                description="Enable Pi 3-specific optimizations (lower resolution, reduced FPS).",
                backward_compat_vars=None,
            )
        )

        self.register(
            FeatureFlag(
                name="PI5_OPTIMIZATION",
                default=False,
                category=FeatureFlagCategory.HARDWARE_OPTIMIZATION,
                description="Enable Pi 5-specific optimizations (higher resolution, increased FPS).",
                backward_compat_vars=None,
            )
        )

        self.register(
            FeatureFlag(
                name="MULTI_CAMERA_SUPPORT",
                default=False,
                category=FeatureFlagCategory.HARDWARE_OPTIMIZATION,
                description="Enable support for multiple camera inputs.",
                backward_compat_vars=None,
            )
        )

        # DEVELOPER TOOLS FLAGS
        self.register(
            FeatureFlag(
                name="DEBUG_LOGGING",
                default=False,
                category=FeatureFlagCategory.DEVELOPER_TOOLS,
                description="Enable DEBUG-level logging for detailed diagnostics.",
                backward_compat_vars=None,
            )
        )

        self.register(
            FeatureFlag(
                name="TRACE_LOGGING",
                default=False,
                category=FeatureFlagCategory.DEVELOPER_TOOLS,
                description="Enable TRACE-level logging with function entry/exit points.",
                backward_compat_vars=None,
            )
        )

        self.register(
            FeatureFlag(
                name="PERFORMANCE_PROFILING",
                default=False,
                category=FeatureFlagCategory.DEVELOPER_TOOLS,
                description="Enable CPU/memory profiling for performance analysis.",
                backward_compat_vars=None,
            )
        )

        self.register(
            FeatureFlag(
                name="DEVELOPMENT_MODE",
                default=False,
                category=FeatureFlagCategory.DEVELOPER_TOOLS,
                description="Enable development mode with relaxed validation and verbose output.",
                backward_compat_vars=None,
            )
        )

        # INTEGRATION COMPATIBILITY FLAGS
        self.register(
            FeatureFlag(
                name="CORS_SUPPORT",
                default=True,
                category=FeatureFlagCategory.INTEGRATION_COMPATIBILITY,
                description="Enable CORS headers for cross-origin requests.",
                backward_compat_vars=None,
            )
        )

        self.register(
            FeatureFlag(
                name="OCTOPRINT_COMPATIBILITY",
                default=False,
                category=FeatureFlagCategory.INTEGRATION_COMPATIBILITY,
                description="Enable OctoPrint camera format compatibility mode.",
                backward_compat_vars=["OCTOPRINT_COMPATIBILITY"],
            )
        )

        self.register(
            FeatureFlag(
                name="HOME_ASSISTANT_INTEGRATION",
                default=False,
                category=FeatureFlagCategory.INTEGRATION_COMPATIBILITY,
                description="Enable Home Assistant-specific endpoint optimizations.",
                backward_compat_vars=None,
            )
        )

        # OBSERVABILITY FLAGS
        self.register(
            FeatureFlag(
                name="PROMETHEUS_METRICS",
                default=False,
                category=FeatureFlagCategory.OBSERVABILITY,
                description="Enable Prometheus-format metrics export.",
                backward_compat_vars=None,
            )
        )

        self.register(
            FeatureFlag(
                name="ENHANCED_FRAME_STATS",
                default=False,
                category=FeatureFlagCategory.OBSERVABILITY,
                description="Enable per-frame processing time statistics.",
                backward_compat_vars=None,
            )
        )

        self.register(
            FeatureFlag(
                name="REQUEST_TRACING",
                default=False,
                category=FeatureFlagCategory.OBSERVABILITY,
                description="Enable detailed request lifecycle tracing.",
                backward_compat_vars=None,
            )
        )

        # GRADUAL ROLLOUT FLAGS
        self.register(
            FeatureFlag(
                name="NEW_STREAMING_API",
                default=False,
                category=FeatureFlagCategory.GRADUAL_ROLLOUT,
                description="Enable new streaming API endpoints (v2).",
                backward_compat_vars=None,
            )
        )

        self.register(
            FeatureFlag(
                name="ALTERNATIVE_PROTOCOLS",
                default=False,
                category=FeatureFlagCategory.GRADUAL_ROLLOUT,
                description="Enable alternative streaming protocols (RTSP, HLS, WebRTC).",
                backward_compat_vars=None,
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
            raise ValueError(f"Feature flag '{flag.name}' already registered")

        if not flag.name:
            raise ValueError("Feature flag name cannot be empty")

        self._flags[flag.name] = flag

        # Register backward compatibility mappings
        if flag.backward_compat_vars:
            for legacy_var in flag.backward_compat_vars:
                if legacy_var in self._legacy_mappings:
                    raise ValueError(
                        f"Legacy variable '{legacy_var}' mapped to multiple flags: "
                        f"'{self._legacy_mappings[legacy_var]}' and '{flag.name}'"
                    )
                self._legacy_mappings[legacy_var] = flag.name

    def load(self) -> None:
        """Load all feature flags from environment variables.

        Supports both MOTION_IN_OCEAN_ prefixed and legacy variable names for
        backward compatibility.
        """
        if self._loaded:
            logger.warning("Feature flags already loaded, skipping reload")
            return

        for flag_name, flag in self._flags.items():
            # Try MOTION_IN_OCEAN_ prefixed name first
            env_var = f"MOTION_IN_OCEAN_{flag_name}"
            value = os.environ.get(env_var)

            # Fall back to backward compatibility names
            if value is None and flag.backward_compat_vars:
                for legacy_var in flag.backward_compat_vars:
                    value = os.environ.get(legacy_var)
                    if value is not None:
                        logger.debug(
                            f"Feature flag '{flag_name}' loaded from legacy "
                            f"variable '{legacy_var}'"
                        )
                        break

            # Parse the value
            if value is not None:
                flag.enabled = self._parse_bool(value, flag.name)
                logger.debug(f"Feature flag '{flag_name}' = {flag.enabled} (from environment)")
            else:
                flag.enabled = flag.default
                logger.debug(f"Feature flag '{flag_name}' = {flag.enabled} (default)")

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
        elif value_lower in ("false", "0", "f", "no", "off"):
            return False
        else:
            logger.warning(
                f"Invalid boolean value '{value}' for feature flag '{flag_name}'. "
                f"Valid values: true, 1, t, yes, on, false, 0, f, no, off. "
                f"Using default {self._flags[flag_name].default}"
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
            raise KeyError(f"Unknown feature flag: {flag_name}")

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
            name: flag.enabled
            for name, flag in self._flags.items()
            if flag.category == category
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

    def _log_summary(self) -> None:
        """Log a summary of loaded feature flags grouped by category."""
        if not self._loaded:
            return

        logger.info("Feature Flags Loaded:")
        for category in FeatureFlagCategory:
            flags_in_category = self.get_flags_by_category(category)
            if flags_in_category:
                enabled_count = sum(1 for v in flags_in_category.values() if v)
                status = " | ".join(
                    f"{name}={enabled}" for name, enabled in sorted(flags_in_category.items())
                )
                logger.debug(
                    f"  {category.value}: ({enabled_count}/{len(flags_in_category)} enabled) | {status}"
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
_feature_flags: Optional[FeatureFlags] = None


def get_feature_flags() -> FeatureFlags:
    """Get the global feature flags instance (lazy initialization).

    Returns:
        FeatureFlags instance.
    """
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = FeatureFlags()
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
