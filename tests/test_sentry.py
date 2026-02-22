"""Integration tests for Sentry error tracking integration."""

from unittest import mock


class TestSentryIntegration:
    """Test Sentry error tracking initialization and behavior."""

    def test_sentry_skips_init_when_dsn_missing(self):
        """Sentry should skip SDK initialization when DSN is empty or None."""
        from pi_camera_in_docker.sentry_config import init_sentry

        with mock.patch("sentry_sdk.init") as mock_init:
            init_sentry("", "webcam")
            init_sentry(None, "webcam")
            mock_init.assert_not_called()

    def test_sentry_initializes_with_valid_dsn(self):
        """Sentry should initialize SDK and tag app mode after init."""
        from pi_camera_in_docker.sentry_config import init_sentry

        # Mock DSN (not real, but valid format)
        test_dsn = "https://test-key@o0.ingest.sentry.io/0"

        with (
            mock.patch("sentry_sdk.init") as mock_init,
            mock.patch("sentry_sdk.set_tag") as mock_set_tag,
        ):
            init_sentry(test_dsn, "webcam")

            # Verify init was called with expected parameters
            mock_init.assert_called_once()
            call_kwargs = mock_init.call_args[1]
            assert call_kwargs["dsn"] == test_dsn
            assert "integrations" in call_kwargs
            assert "before_send" in call_kwargs
            assert "before_breadcrumb" in call_kwargs
            assert "environment" in call_kwargs
            assert "traces_sample_rate" in call_kwargs
            assert "send_default_pii" in call_kwargs
            mock_set_tag.assert_called_once_with("app_mode", "webcam")

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
                    "MIO_WEBCAM_CONTROL_PLANE_AUTH_TOKEN": "secret-value",
                    "MIO_MANAGEMENT_AUTH_TOKEN": "secret-value-2",
                    "MIO_DISCOVERY_TOKEN": "secret-value-3",
                    "MIO_SENTRY_DSN": "https://secret@example.com/1",
                    "WEBCAM_CONTROL_PLANE_AUTH_TOKEN": "legacy-secret",
                    "SENTRY_DSN": "https://legacy@example.com/1",
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

        # Verify canonical and legacy env vars are redacted
        assert filtered["contexts"]["env"]["MIO_WEBCAM_CONTROL_PLANE_AUTH_TOKEN"] == "[REDACTED]"
        assert filtered["contexts"]["env"]["MIO_MANAGEMENT_AUTH_TOKEN"] == "[REDACTED]"
        assert filtered["contexts"]["env"]["MIO_DISCOVERY_TOKEN"] == "[REDACTED]"
        assert filtered["contexts"]["env"]["MIO_SENTRY_DSN"] == "[REDACTED]"
        assert filtered["contexts"]["env"]["WEBCAM_CONTROL_PLANE_AUTH_TOKEN"] == "[REDACTED]"
        assert filtered["contexts"]["env"]["SENTRY_DSN"] == "[REDACTED]"

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
