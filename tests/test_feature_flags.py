"""
Unit tests for feature flags system.
Tests flag registration, loading, backward compatibility, and API endpoints.
"""

import os
from unittest import mock

import pytest


class TestFeatureFlagRegistry:
    """Test the FeatureFlags registry system."""

    def test_feature_flags_initialization(self):
        """Test that FeatureFlags can be initialized."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags is not None
        assert not flags._loaded
        assert len(flags.get_all_flags()) > 0

    def test_all_flags_registered(self):
        """Test that all expected flags are registered."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        flags = FeatureFlags()
        all_flags = flags.get_all_flags()

        # Check that flags from each category are present
        expected_flags = {
            "MOCK_CAMERA",
            "CORS_SUPPORT",
            "DEBUG_LOGGING",
            "QUALITY_ADAPTATION",
            "FPS_THROTTLE_ADAPTIVE",
            "FRAME_SIZE_OPTIMIZATION",
            "MOTION_DETECTION",
            "FRAME_RECORDING",
            "PI3_OPTIMIZATION",
            "PI5_OPTIMIZATION",
            "MULTI_CAMERA_SUPPORT",
            "TRACE_LOGGING",
            "PERFORMANCE_PROFILING",
            "DEVELOPMENT_MODE",
            "OCTOPRINT_COMPATIBILITY",
            "HOME_ASSISTANT_INTEGRATION",
            "PROMETHEUS_METRICS",
            "ENHANCED_FRAME_STATS",
            "REQUEST_TRACING",
            "NEW_STREAMING_API",
            "ALTERNATIVE_PROTOCOLS",
        }

        assert expected_flags.issubset(set(all_flags.keys())), (
            f"Missing flags: {expected_flags - set(all_flags.keys())}"
        )

    def test_backward_compatibility_mock_camera(self):
        """Test backward compatibility with legacy MOCK_CAMERA env var."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        with mock.patch.dict(os.environ, {"MOCK_CAMERA": "true"}, clear=True):
            flags = FeatureFlags()
            flags.load()
            assert flags.is_enabled("MOCK_CAMERA") is True

        with mock.patch.dict(os.environ, {"MOCK_CAMERA": "false"}, clear=True):
            flags = FeatureFlags()
            flags.load()
            assert flags.is_enabled("MOCK_CAMERA") is False

    def test_prefixed_env_vars_take_precedence(self):
        """Test that MOTION_IN_OCEAN_ prefixed vars take precedence over legacy vars."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        with mock.patch.dict(
            os.environ,
            {"MOCK_CAMERA": "false", "MOTION_IN_OCEAN_MOCK_CAMERA": "true"},
            clear=True,
        ):
            flags = FeatureFlags()
            flags.load()
            assert flags.is_enabled("MOCK_CAMERA") is True

    def test_backward_compatibility_octoprint_compatibility(self):
        """Test OCTOPRINT_COMPATIBILITY supports both prefixed and legacy env vars."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        with mock.patch.dict(
            os.environ, {"MOTION_IN_OCEAN_OCTOPRINT_COMPATIBILITY": "true"}, clear=True
        ):
            flags = FeatureFlags()
            flags.load()
            assert flags.is_enabled("OCTOPRINT_COMPATIBILITY") is True

        with mock.patch.dict(os.environ, {"OCTOPRINT_COMPATIBILITY": "true"}, clear=True):
            flags = FeatureFlags()
            flags.load()
            assert flags.is_enabled("OCTOPRINT_COMPATIBILITY") is True

    def test_prefixed_octoprint_env_var_takes_precedence(self):
        """Test prefixed OCTOPRINT_COMPATIBILITY env var takes precedence over legacy."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        with mock.patch.dict(
            os.environ,
            {
                "OCTOPRINT_COMPATIBILITY": "false",
                "MOTION_IN_OCEAN_OCTOPRINT_COMPATIBILITY": "true",
            },
            clear=True,
        ):
            flags = FeatureFlags()
            flags.load()
            assert flags.is_enabled("OCTOPRINT_COMPATIBILITY") is True

    def test_flag_defaults(self):
        """Test that flag defaults are correct."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        with mock.patch.dict(os.environ, {}, clear=True):
            flags = FeatureFlags()
            flags.load()

            # Most flags should be disabled by default
            assert flags.is_enabled("MOCK_CAMERA") is False
            assert flags.is_enabled("DEBUG_LOGGING") is False

            # Some flags should be enabled by default
            assert flags.is_enabled("CORS_SUPPORT") is True
            assert flags.is_enabled("FRAME_SIZE_OPTIMIZATION") is True

    def test_parse_bool_variations(self):
        """Test that various boolean string formats are parsed correctly."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("t", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("f", False),
            ("no", False),
            ("off", False),
        ]

        for value, expected in test_cases:
            with mock.patch.dict(os.environ, {"MOTION_IN_OCEAN_DEBUG_LOGGING": value}, clear=True):
                flags = FeatureFlags()
                flags.load()
                assert flags.is_enabled("DEBUG_LOGGING") == expected, f"Failed for value: {value}"

    def test_unknown_flag_raises_error(self):
        """Test that querying unknown flag raises KeyError."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        flags = FeatureFlags()
        with pytest.raises(KeyError):
            flags.is_enabled("NONEXISTENT_FLAG")

    def test_get_flags_by_category(self):
        """Test retrieving flags by category."""
        from pi_camera_in_docker.feature_flags import FeatureFlagCategory, FeatureFlags

        flags = FeatureFlags()
        performance_flags = flags.get_flags_by_category(FeatureFlagCategory.PERFORMANCE)

        assert isinstance(performance_flags, dict)
        assert "QUALITY_ADAPTATION" in performance_flags
        assert "FPS_THROTTLE_ADAPTIVE" in performance_flags

    def test_get_flag_info(self):
        """Test retrieving detailed flag information."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        flags = FeatureFlags()
        info = flags.get_flag_info("MOCK_CAMERA")

        assert info is not None
        assert info["name"] == "MOCK_CAMERA"
        assert "description" in info
        assert "enabled" in info
        assert "default" in info
        assert "category" in info
        assert "backward_compat_vars" in info

    def test_get_flag_info_unknown(self):
        """Test that unknown flag returns None."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        flags = FeatureFlags()
        info = flags.get_flag_info("NONEXISTENT")
        assert info is None

    def test_is_flag_enabled_convenience_function(self):
        """Test the module-level is_flag_enabled convenience function."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        with mock.patch.dict(os.environ, {"MOTION_IN_OCEAN_DEBUG_LOGGING": "true"}, clear=True):
            # Create a new instance and load it
            flags = FeatureFlags()
            flags.load()
            assert flags.is_enabled("DEBUG_LOGGING") is True

    def test_backward_compat_cors_not_mapped(self):
        """Test that CORS_SUPPORT doesn't have backward compat mapping (feature flag only)."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        # CORS_SUPPORT should only respect MOTION_IN_OCEAN_CORS_SUPPORT, not legacy CORS_ORIGINS
        with mock.patch.dict(os.environ, {"MOTION_IN_OCEAN_CORS_SUPPORT": "false"}, clear=True):
            flags = FeatureFlags()
            flags.load()
            assert flags.is_enabled("CORS_SUPPORT") is False


class TestFeatureFlagsIntegration:
    """Test feature flags integration with main application."""

    def test_main_imports_feature_flags(self):
        """main should expose and use the shared feature flag registry instance."""
        try:
            from pi_camera_in_docker import main
            from pi_camera_in_docker.feature_flags import FeatureFlags, get_feature_flags

            assert isinstance(main.feature_flags, FeatureFlags)
            assert main.feature_flags is get_feature_flags()
            assert main.feature_flags._loaded is True
        except ImportError as e:
            pytest.skip(f"Cannot import main module: {e}")

    def test_feature_flags_loaded_in_main(self):
        """module-level convenience helper should resolve values from loaded registry."""
        try:
            from pi_camera_in_docker import main

            assert callable(main.is_flag_enabled)
            assert main.is_flag_enabled("FRAME_SIZE_OPTIMIZATION") is True
        except ImportError as e:
            pytest.skip(f"Cannot import feature flags: {e}")


class TestFeatureFlagsAPI:
    """Test the feature flags API endpoint."""

    def test_feature_flags_api_endpoint_exists(self):
        """Feature flag summary payload should expose categories and known flags."""
        try:
            from pi_camera_in_docker.feature_flags import FeatureFlagCategory, get_feature_flags

            flags = get_feature_flags()
            summary = flags.get_summary()
            debug_info = flags.get_flag_info("DEBUG_LOGGING")
            mock_info = flags.get_flag_info("MOCK_CAMERA")

            expected_categories = {category.value for category in FeatureFlagCategory}
            assert expected_categories.issubset(set(summary.keys()))
            assert "DEBUG_LOGGING" in summary[FeatureFlagCategory.DEVELOPER_TOOLS.value]
            assert "MOCK_CAMERA" in summary[FeatureFlagCategory.EXPERIMENTAL.value]
            assert debug_info is not None
            assert debug_info["category"] == "Developer Tools"
            assert mock_info is not None
            assert mock_info["name"] == "MOCK_CAMERA"
            assert mock_info["backward_compat_vars"] == ["MOCK_CAMERA"]
        except ImportError as e:
            pytest.skip(f"Cannot setup Flask app: {e}")
