"""
Unit tests for feature flags system.
Tests flag registration, loading, backward compatibility, and API endpoints.
"""

import os
from unittest import mock

import pytest


class TestFeatureFlagRegistry:
    """Test the FeatureFlags registry system."""

    def test_get_flags_by_category_returns_only_matching_flags(self, monkeypatch):
        """Category lookup returns enabled states for flags in the requested category."""
        from pi_camera_in_docker.feature_flags import (
            FeatureFlag,
            FeatureFlagCategory,
            FeatureFlags,
        )

        monkeypatch.setenv("MIO_PERFORMANCE_PROBE", "true")
        flags = FeatureFlags()
        flags.register(
            FeatureFlag(
                name="PERFORMANCE_PROBE",
                default=False,
                category=FeatureFlagCategory.PERFORMANCE,
                description="Test performance category filtering.",
            )
        )
        flags.register(
            FeatureFlag(
                name="EXPERIMENTAL_PROBE",
                default=True,
                category=FeatureFlagCategory.EXPERIMENTAL,
                description="Test exclusion of flags in other categories.",
            )
        )
        flags.load()

        assert flags.get_flags_by_category(FeatureFlagCategory.PERFORMANCE) == {
            "PERFORMANCE_PROBE": True
        }

    def test_canonical_mock_camera_env_controls_flag_state(self):
        """Canonical MIO_MOCK_CAMERA env var should control MOCK_CAMERA feature flag state."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        with mock.patch.dict(os.environ, {"MIO_MOCK_CAMERA": "true"}, clear=True):
            flags = FeatureFlags()
            flags.load()
            assert flags.is_enabled("MOCK_CAMERA") is True

        with mock.patch.dict(os.environ, {"MIO_MOCK_CAMERA": "false"}, clear=True):
            flags = FeatureFlags()
            flags.load()
            assert flags.is_enabled("MOCK_CAMERA") is False

    def test_no_deprecation_warning_when_using_canonical_mio_vars(self, caplog):
        """Canonical MIO_ variables should not produce legacy alias deprecation warnings."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        with mock.patch.dict(os.environ, {"MIO_MOCK_CAMERA": "true"}, clear=True):
            flags = FeatureFlags()
            with caplog.at_level("WARNING"):
                flags.load()

        assert flags.is_enabled("MOCK_CAMERA") is True
        assert "Legacy environment variable" not in caplog.text

    @pytest.mark.parametrize(
        "env_var",
        ["MIO_OCTOPRINT_COMPATIBILITY", "OCTOPRINT_COMPATIBILITY"],
    )
    def test_deprecated_octoprint_compatibility_env_vars_are_ignored_silently(
        self, caplog, env_var
    ):
        """Deprecated OctoPrint env vars should be ignored without startup warnings."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        with mock.patch.dict(os.environ, {env_var: "true"}, clear=True):
            flags = FeatureFlags()
            with caplog.at_level("WARNING"):
                flags.load()

        assert flags.is_enabled("MOCK_CAMERA") is False
        assert not [r.message for r in caplog.records if r.levelname == "WARNING"]

    def test_deprecated_octoprint_compatibility_vars_are_ignored_silently_together(self, caplog):
        """Multiple deprecated OctoPrint env vars should still be ignored silently."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        with mock.patch.dict(
            os.environ,
            {
                "MIO_OCTOPRINT_COMPATIBILITY": "true",
                "OCTOPRINT_COMPATIBILITY": "true",
            },
            clear=True,
        ):
            flags = FeatureFlags()
            with caplog.at_level("WARNING"):
                flags.load()

        assert flags.is_enabled("MOCK_CAMERA") is False
        assert not [r.message for r in caplog.records if r.levelname == "WARNING"]


class TestFeatureFlagBehavior:
    """General feature-flag behavior tests."""

    def test_flag_defaults(self):
        """Test that flag defaults are correct."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        with mock.patch.dict(os.environ, {}, clear=True):
            flags = FeatureFlags()
            flags.load()

            # Most flags should be disabled by default
            assert flags.is_enabled("MOCK_CAMERA") is False

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
            with mock.patch.dict(os.environ, {"MIO_MOCK_CAMERA": value}, clear=True):
                flags = FeatureFlags()
                flags.load()
                assert flags.is_enabled("MOCK_CAMERA") == expected, f"Failed for value: {value}"

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
        assert performance_flags == {}

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

    @pytest.mark.parametrize(
        ("environment", "expected"),
        [
            ({"MIO_MOCK_CAMERA": "true"}, True),
            ({}, False),
        ],
    )
    def test_is_flag_enabled_convenience_function(self, environment, expected):
        """Test the module-level is_flag_enabled convenience function."""
        from pi_camera_in_docker import feature_flags

        with mock.patch.dict(os.environ, environment, clear=True):
            isolated_registry = feature_flags.FeatureFlags()
            isolated_registry.load()
            with mock.patch.object(feature_flags, "_feature_flags", isolated_registry):
                assert feature_flags.is_flag_enabled("MOCK_CAMERA") is expected

    def test_cors_support_removed_from_feature_flag_registry(self):
        """CORS support should no longer be represented as a feature flag."""
        from pi_camera_in_docker.feature_flags import FeatureFlags

        flags = FeatureFlags()

        with pytest.raises(KeyError):
            flags.is_enabled("CORS_SUPPORT")


class TestFeatureFlagsIntegration:
    """Test feature flags integration with main application."""

    def test_mock_camera_env_flag_changes_main_runtime_config(self, monkeypatch):
        """MOCK_CAMERA feature flag should be reflected in main runtime config."""
        import importlib

        monkeypatch.setenv("MIO_MOCK_CAMERA", "true")
        monkeypatch.setenv("MIO_APP_MODE", "webcam")

        feature_flags_module = importlib.import_module("pi_camera_in_docker.feature_flags")
        main_module = importlib.import_module("pi_camera_in_docker.main")

        importlib.reload(feature_flags_module)
        reloaded_main = importlib.reload(main_module)

        cfg = reloaded_main._load_config()
        assert cfg["mock_camera"] is True
