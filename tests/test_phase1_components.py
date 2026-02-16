"""
Phase 1: Observability & Foundation - Comprehensive Tests

Tests for:
1.3 Configuration Validation
1.4 API Rate Limiting
"""

import sys
from pathlib import Path

import pytest
from flask import Flask


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pi_camera_in_docker.config_validator import (
    ConfigValidationError,
    validate_all_config,
    validate_discovery_config,
    validate_settings_patch,
)


class TestConfigValidator:
    """Tests for configuration validation (1.3)"""

    def test_validate_discovery_config_enabled_complete(self):
        """Test valid discovery config when enabled"""
        config = {
            "discovery_enabled": True,
            "discovery_management_url": "http://localhost:8000",
            "discovery_token": "token123456",
            "base_url": "http://webcam:8000",
        }
        # Should not raise
        validate_discovery_config(config)

    def test_validate_discovery_config_missing_url(self):
        """Test discovery config missing required URL when enabled"""
        config = {
            "discovery_enabled": True,
            "discovery_token": "token123456",
            "base_url": "http://webcam:8000",
            # Missing DISCOVERY_MANAGEMENT_URL
        }
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_discovery_config(config)
        assert "DISCOVERY_MANAGEMENT_URL" in str(exc_info.value)

    def test_validate_discovery_config_disabled_partial(self):
        """Test that discovery config validation is skipped when disabled"""
        config = {
            "discovery_enabled": False,
            # Missing required fields, but should not raise
        }
        # Should not raise
        validate_discovery_config(config)

    def test_validate_all_config_valid_webcam(self):
        """Test valid webcam configuration"""
        config = {
            "app_mode": "webcam",
            "resolution": (1920, 1080),
            "fps": 30,
            "discovery_enabled": False,
        }
        # Should not raise
        validate_all_config(config)

    def test_validate_all_config_valid_management(self):
        """Test valid management configuration"""
        config = {
            "app_mode": "management",
            "discovery_enabled": False,
        }
        # Should not raise
        validate_all_config(config)

    def test_validate_all_config_discovery_enabled_missing_management_url_raises(self):
        """validate_all_config should reject discovery enabled config missing management URL."""
        config = {
            "app_mode": "webcam",
            "resolution": (1920, 1080),
            "fps": 30,
            "discovery_enabled": True,
            "discovery_token": "token123456",
            "base_url": "http://webcam:8000",
        }
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_all_config(config)
        assert "DISCOVERY_MANAGEMENT_URL" in str(exc_info.value)

    def test_validate_settings_patch_package_import_path(self):
        """Test validate_settings_patch via package import path."""
        # Valid value should produce no validation errors
        errors = validate_settings_patch({"camera": {"fps": 30}})
        assert errors == {}

    def test_validate_all_config_discovery_enabled_missing_token_raises(self):
        """validate_all_config should reject discovery enabled config missing discovery token."""
        config = {
            "app_mode": "webcam",
            "resolution": (1920, 1080),
            "fps": 30,
            "discovery_enabled": True,
            "discovery_management_url": "http://localhost:8000",
            "base_url": "http://webcam:8000",
        }
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_all_config(config)
        assert "DISCOVERY_TOKEN" in str(exc_info.value)


class TestRateLimiting:
    """Tests for API rate limiting (1.4)"""

    def test_rate_limiting_applies_expected_limits_to_management_routes(self, tmp_path):
        """register_management_routes should apply route-specific limits when limiter is provided."""
        from flask import Flask

        from pi_camera_in_docker.management_api import register_management_routes

        class RecordingLimiter:
            def __init__(self):
                self.applied_limits = []

            def limit(self, limit_str):
                def decorator(func):
                    self.applied_limits.append((func.__name__, limit_str))
                    return func

                return decorator

        app = Flask(__name__)
        limiter = RecordingLimiter()
        register_management_routes(
            app=app,
            registry_path=str(tmp_path / "node-registry.json"),
            auth_token="",
            node_discovery_shared_secret="discovery-secret",
            limiter=limiter,
        )

        applied = dict(limiter.applied_limits)
        assert applied.get("announce_node") == "10/minute"
        assert applied.get("list_nodes") == "1000/minute"
        assert applied.get("node_status") == "1000/minute"
        assert "100/minute" in applied.values()
        assert len(limiter.applied_limits) >= 8


class TestConfigValidationHints:
    """Tests for user-friendly error hints in config validation"""

    def test_discovery_missing_base_url_includes_hint(self):
        """Test that discovery/base-url validation returns helpful hints."""
        config = {
            "discovery_enabled": True,
            "discovery_management_url": "http://localhost:8000",
            "discovery_token": "token123456",
            # Missing base_url
        }
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_all_config(config)

        assert "BASE_URL" in str(exc_info.value)
        assert exc_info.value.hint is not None

    def test_discovery_config_error_includes_hint(self):
        """Test that discovery config error includes helpful hint"""
        config = {
            "discovery_enabled": True,
            "discovery_management_url": "http://localhost:8000",
            "base_url": "http://webcam:8000",
            # Missing token
        }
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_discovery_config(config)

        assert "DISCOVERY_TOKEN" in str(exc_info.value)
        assert exc_info.value.hint is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
