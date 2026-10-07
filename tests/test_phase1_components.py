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
from pi_camera_in_docker.rate_limiter import InMemoryRateLimiter


class TestConfigValidator:
    """Tests for configuration validation (1.3)"""

    @pytest.mark.parametrize(
        "config",
        [
            {
                "discovery_enabled": True,
                "discovery_management_url": "http://localhost:8000",
                "discovery_token": "token123456",
                "base_url": "http://webcam:8000",
            },
            {
                "discovery_enabled": False,
            },
        ],
    )
    def test_validate_discovery_config_accepts_valid_config_per_mode(self, config):
        """validate_discovery_config should accept complete enabled config and disabled partial config."""
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

    @pytest.mark.parametrize(
        "config",
        [
            {
                "app_mode": "webcam",
                "resolution": (1920, 1080),
                "fps": 30,
                "discovery_enabled": False,
            },
            {
                "app_mode": "management",
                "discovery_enabled": False,
            },
        ],
    )
    def test_validate_all_config_accepts_valid_base_configs(self, config):
        """validate_all_config should accept valid webcam and management base configurations."""
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

    def test_validate_settings_patch_reports_valid_and_invalid_values(self):
        """validate_settings_patch should accept valid values and report invalid ones."""
        valid_errors = validate_settings_patch(
            {
                "camera": {"fps": 30, "resolution": "1280x720"},
                "discovery": {"discovery_management_url": "http://management.local:8001"},
            }
        )
        assert valid_errors == {}

        invalid_errors = validate_settings_patch({"camera": {"fps": "invalid"}})
        assert "camera.fps" in invalid_errors

        invalid_resolution_errors = validate_settings_patch(
            {"camera": {"resolution": "1280-by-720"}}
        )
        assert "camera.resolution" in invalid_resolution_errors

        invalid_uri_errors = validate_settings_patch(
            {"discovery": {"discovery_management_url": "not-a-uri"}}
        )
        assert "discovery.discovery_management_url" in invalid_uri_errors

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

    def test_discovery_announcements_are_limited_to_ten_per_minute(self, tmp_path):
        """A discovery client receives 429 after the per-minute announcement quota.

        Traceability: docs/product/PRD-backend.md#api-request-limits-p2.
        """
        from pi_camera_in_docker.management_api import register_management_routes

        now = [100.0]
        app = Flask(__name__)
        limiter = InMemoryRateLimiter(clock=lambda: now[0], key_func=lambda: "discovery-client")
        register_management_routes(
            app=app,
            registry_path=str(tmp_path / "node-registry.json"),
            auth_token="",
            node_discovery_shared_secret="discovery-secret",
            limiter=limiter,
        )

        client = app.test_client()
        headers = {"Authorization": "Bearer discovery-secret"}
        url = "/api/v1/discovery/announce"

        for _ in range(10):
            response = client.post(url, headers=headers, json={})
            assert response.status_code == 400

        limited = client.post(url, headers=headers, json={})
        assert limited.status_code == 429
        assert limited.get_json()["error"] == "RATE_LIMITED"
        assert limited.headers["Retry-After"] == "60"

        now[0] = 161.0
        assert client.post(url, headers=headers, json={}).status_code == 400


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
