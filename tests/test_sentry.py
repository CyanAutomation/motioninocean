"""Integration tests for Sentry error tracking integration."""

from unittest import mock


class TestSentryIntegration:
    """Test Sentry error tracking initialization and behavior."""

    def test_sentry_disabled_when_dsn_empty(self):
        """Sentry should be disabled when SENTRY_DSN is empty."""
        from pi_camera_in_docker.sentry_config import init_sentry

        # This should not raise and should not initialize SDK
        init_sentry("", "webcam")

    def test_sentry_disabled_when_dsn_none(self):
        """Sentry should be disabled when SENTRY_DSN is None."""
        from pi_camera_in_docker.sentry_config import init_sentry

        # This should not raise
        init_sentry(None, "webcam")

    def test_sentry_initializes_with_valid_dsn(self):
        """Sentry should initialize when valid DSN is provided."""
        from pi_camera_in_docker.sentry_config import init_sentry

        # Mock DSN (not real, but valid format)
        test_dsn = "https://test-key@o0.ingest.sentry.io/0"

        with mock.patch("sentry_sdk.init") as mock_init:
            init_sentry(test_dsn, "webcam")

            # Verify init was called with correct parameters
            mock_init.assert_called_once()
            call_kwargs = mock_init.call_args[1]
            assert call_kwargs["dsn"] == test_dsn
            assert call_kwargs["tags"]["app_mode"] == "webcam"

    def test_sentry_captures_auth_token_redaction(self):
        """Auth tokens should be redacted from Sentry events."""
        from pi_camera_in_docker.sentry_config import _redact_auth_data

        # Test event with auth token
        event = {
            "request": {
                "headers": {
                    "Authorization": "Bearer secret-token-123",
                    "Content-Type": "application/json",
                },
                "url": "http://example.com/api?token=abc123&other=value",
            },
            "contexts": {
                "env": {
                    "WEBCAM_CONTROL_PLANE_AUTH_TOKEN": "secret-value",
                    "OTHER_VAR": "visible",
                }
            },
        }

        filtered = _redact_auth_data(event, {})

        # Verify auth header is redacted
        assert filtered["request"]["headers"]["Authorization"] == "[REDACTED]"

        # Verify token query param is redacted
        assert "token=abc123" not in filtered["request"]["url"]
        assert "token=[REDACTED]" in filtered["request"]["url"]

        # Verify env var is redacted
        assert filtered["contexts"]["env"]["WEBCAM_CONTROL_PLANE_AUTH_TOKEN"] == "[REDACTED]"

        # Verify other vars are preserved
        assert filtered["request"]["headers"]["Content-Type"] == "application/json"
        assert filtered["contexts"]["env"]["OTHER_VAR"] == "visible"

    def test_sentry_filters_health_breadcrumbs(self):
        """Health/ready/metrics endpoints should be filtered from breadcrumbs."""
        from pi_camera_in_docker.sentry_config import _breadcrumb_filter

        # Test health endpoint breadcrumb
        health_crumb = {
            "category": "http.client",
            "data": {"url": "http://localhost:8000/health"},
        }
        assert _breadcrumb_filter(health_crumb, {}) is None

        # Test ready endpoint breadcrumb
        ready_crumb = {
            "category": "http.client",
            "data": {"url": "http://localhost:8000/ready"},
        }
        assert _breadcrumb_filter(ready_crumb, {}) is None

        # Test normal endpoint breadcrumb (should be preserved)
        normal_crumb = {
            "category": "http.client",
            "data": {"url": "http://localhost:8000/api/status"},
        }
        assert _breadcrumb_filter(normal_crumb, {}) is not None
