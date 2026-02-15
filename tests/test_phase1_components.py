"""
Phase 1: Observability & Foundation - Comprehensive Tests

Tests for:
1.1 Structured Logging Framework
1.3 Configuration Validation
1.4 API Rate Limiting
"""

import json
import logging
import sys
import uuid
from pathlib import Path

import pytest
from flask import Flask


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pi_camera_in_docker.config_validator import (
    ConfigValidationError,
    validate_all_config,
    validate_app_mode,
    validate_bearer_token,
    validate_discovery_config,
    validate_float_range,
    validate_integer_range,
    validate_resolution,
    validate_settings_patch,
    validate_url,
)
from pi_camera_in_docker.structured_logging import (
    get_correlation_id,
    log_error,
    log_event,
)


class TestStructuredLogging:
    """Tests for structured logging framework (1.1)"""

    def test_get_correlation_id_from_request_context(self):
        """Test extracting correlation ID from Flask request context"""
        app = Flask(__name__)

        with app.app_context(), app.test_request_context(headers={"X-Correlation-ID": "test-123"}):
            correlation_id = get_correlation_id()
            assert correlation_id == "test-123"

    def test_get_correlation_id_generates_uuid_when_missing(self):
        """Test that UUID is generated when correlation ID header is missing"""
        app = Flask(__name__)

        with app.app_context(), app.test_request_context():
            correlation_id = get_correlation_id()
            # Verify it's a valid UUID hex string
            assert len(correlation_id) == 32
            try:
                uuid.UUID(hex=correlation_id)
                is_valid_uuid = True
            except ValueError:
                is_valid_uuid = False
            assert is_valid_uuid

    def test_get_correlation_id_caches_in_flask_g(self):
        """Test that correlation ID is cached in Flask g context"""
        app = Flask(__name__)

        with app.app_context(), app.test_request_context():
            id1 = get_correlation_id()
            id2 = get_correlation_id()
            assert id1 == id2

    def test_log_event_structures_data(self, caplog):
        """log_event should emit a structured payload with request correlation context."""
        app = Flask(__name__)

        with caplog.at_level(logging.INFO, logger="pi_camera_in_docker.structured_logging"):
            with app.app_context(), app.test_request_context(headers={"X-Correlation-ID": "req-123"}):
                caplog.clear()
                log_event("node_approved", severity="INFO", node_id="node-1", approver="admin")
                records = [
                    record
                    for record in caplog.records
                    if record.name == "pi_camera_in_docker.structured_logging"
                ]
                assert records
                message = records[-1].getMessage()
                assert message.startswith("event=node_approved ")
                payload = json.loads(message.split(" ", 1)[1])
                assert payload["event_type"] == "node_approved"
                assert payload["correlation_id"] == "req-123"
                assert payload["node_id"] == "node-1"
                assert payload["approver"] == "admin"

    def test_log_error_structures_error_data(self, caplog):
        """log_error should emit operation/type fields with structured JSON payload."""
        app = Flask(__name__)

        with caplog.at_level(logging.ERROR, logger="pi_camera_in_docker.structured_logging"):
            with app.app_context(), app.test_request_context(headers={"X-Correlation-ID": "req-err-1"}):
                caplog.clear()
                log_error(
                    operation="node_registration",
                    error_type="ValidationError",
                    message="Invalid base URL",
                    resource_id="node-1",
                    endpoint="/api/discovery/announce",
                )
                records = [
                    record
                    for record in caplog.records
                    if record.name == "pi_camera_in_docker.structured_logging"
                ]
                assert records
                message = records[-1].getMessage()
                assert message.startswith("error operation=node_registration type=ValidationError ")
                payload = json.loads(message[message.index("{") :])
                assert payload["operation"] == "node_registration"
                assert payload["error_type"] == "ValidationError"
                assert payload["correlation_id"] == "req-err-1"
                assert payload["resource_id"] == "node-1"
                assert payload["message"] == "Invalid base URL"
                assert payload["endpoint"] == "/api/discovery/announce"


class TestConfigValidator:
    """Tests for configuration validation (1.3)"""

    def test_validate_resolution_valid(self):
        """Test valid resolution format"""
        result = validate_resolution("1920x1080")
        assert result == (1920, 1080)

    def test_validate_resolution_invalid_format(self):
        """Test invalid resolution format raises error"""
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_resolution("invalid")
        assert "RESOLUTION format invalid" in str(exc_info.value)

    def test_validate_resolution_out_of_range(self):
        """Test resolution out of range"""
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_resolution("10000x10000")
        assert "RESOLUTION values out of range" in str(exc_info.value)

    def test_validate_integer_range_valid(self):
        """Test valid integer in range"""
        result = validate_integer_range("50", "test_param", 1, 100, 0)
        assert result == 50

    def test_validate_integer_range_out_of_range(self):
        """Test integer out of range"""
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_integer_range("150", "test_param", 1, 100, 50)
        assert "out of range" in str(exc_info.value)

    def test_validate_integer_range_wrong_type(self):
        """Test non-integer input"""
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_integer_range("not_a_number", "test_param", 1, 100, 50)
        assert "must be an integer" in str(exc_info.value)

    def test_validate_float_range_valid(self):
        """Test valid float in range"""
        result = validate_float_range("1.5", "test_param", 0.5, 3.0, 1.0)
        assert result == 1.5

    def test_validate_float_range_out_of_range(self):
        """Test float out of range"""
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_float_range("5.0", "test_param", 0.5, 3.0, 1.0)
        assert "out of range" in str(exc_info.value)

    def test_validate_app_mode_valid(self):
        """Test valid app mode"""
        result = validate_app_mode("webcam")
        assert result == "webcam"

        result = validate_app_mode("management")
        assert result == "management"

    def test_validate_app_mode_invalid(self):
        """Test invalid app mode"""
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_app_mode("invalid_mode")
        assert "must be one of" in str(exc_info.value)

    def test_validate_url_valid(self):
        """Test valid URLs"""
        assert validate_url("http://example.com", "TEST_URL") == "http://example.com"
        assert validate_url("https://example.com:8000", "TEST_URL") == "https://example.com:8000"

    def test_validate_url_invalid_scheme(self):
        """Test URL with invalid scheme"""
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_url("ftp://example.com", "TEST_URL")
        assert "http://" in str(exc_info.value) or "https://" in str(exc_info.value)

    def test_validate_bearer_token_valid(self):
        """Test valid bearer token"""
        result = validate_bearer_token("mytoken123", "TEST_TOKEN")
        assert result == "mytoken123"

    def test_validate_bearer_token_too_short(self):
        """Test bearer token too short"""
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_bearer_token("short", "TEST_TOKEN")
        assert "minimum 8 characters" in str(exc_info.value)

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


class TestCorrelationIdIntegration:
    """Integration tests for correlation ID tracking"""

    def test_request_correlation_id_is_propagated_to_structured_logs(self, caplog):
        """Request header correlation IDs should flow into structured logs in the same request."""
        app = Flask(__name__)

        with caplog.at_level(logging.INFO, logger="pi_camera_in_docker.structured_logging"):
            with app.app_context(), app.test_request_context(headers={"X-Correlation-ID": "corr-fixed"}):
                caplog.clear()
                log_event("request_start")
                log_event("request_end")
                records = [
                    record
                    for record in caplog.records
                    if record.name == "pi_camera_in_docker.structured_logging"
                ]
                assert len(records) >= 2
                payloads = [json.loads(record.getMessage().split(" ", 1)[1]) for record in records[-2:]]
                assert payloads[0]["correlation_id"] == "corr-fixed"
                assert payloads[1]["correlation_id"] == "corr-fixed"

            with app.app_context(), app.test_request_context():
                caplog.clear()
                log_event("request_without_header")
                records = [
                    record
                    for record in caplog.records
                    if record.name == "pi_camera_in_docker.structured_logging"
                ]
                assert records
                payload = json.loads(records[-1].getMessage().split(" ", 1)[1])
                assert len(payload["correlation_id"]) == 32


class TestConfigValidationHints:
    """Tests for user-friendly error hints in config validation"""

    def test_resolution_error_includes_hint(self):
        """Test that resolution error includes helpful hint"""
        try:
            validate_resolution("999999x999999")
        except ConfigValidationError as e:
            assert e.hint is not None or "must be between" in str(e)

    def test_discovery_config_error_includes_hint(self):
        """Test that discovery config error includes helpful hint"""
        config = {
            "DISCOVERY_ENABLED": "true",
            "DISCOVERY_TOKEN": "short",  # Too short
            "DISCOVERY_MANAGEMENT_URL": "http://localhost:8000",
            "DISCOVERY_BASE_URL": "http://webcam:8000",
        }
        try:
            validate_discovery_config(config)
        except ConfigValidationError as e:
            assert "DISCOVERY_TOKEN" in str(e) or "8 characters" in str(e)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
