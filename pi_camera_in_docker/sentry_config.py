"""Sentry error tracking initialization and configuration.

Provides optional error tracking integration when SENTRY_DSN environment
variable is set. Includes data filtering to redact sensitive auth tokens
while preserving useful debugging context.
"""

import re
from typing import Any, Dict, Optional

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration


def _redact_auth_data(event: Dict[str, Any], _hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Redact sensitive authentication data from Sentry events.

    Redacts:
    - Authorization header values (bearer tokens)
    - Auth token environment variable values

    Preserves:
    - Request paths, hostnames, ports
    - Camera settings, node metadata

    Args:
        event: Sentry event dictionary to filter
        _hint: Additional context (exception, original_exception) - unused but required by API

    Returns:
        Modified event (or None to drop event)
    """
    # Redact Authorization headers from request data
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        if "Authorization" in headers:
            headers["Authorization"] = "[REDACTED]"

    # Redact bearer tokens from request context
    if "request" in event and "url" in event["request"]:
        # Redact tokens in query parameters if present
        url = event["request"]["url"]
        url = re.sub(r"([?&]token=)[^&]+", r"\1[REDACTED]", url)
        event["request"]["url"] = url

    # Redact environment variables containing auth tokens
    if "contexts" in event and "env" in event["contexts"]:
        env_keys_to_redact = {
            "WEBCAM_CONTROL_PLANE_AUTH_TOKEN",
            "MANAGEMENT_AUTH_TOKEN",
            "DISCOVERY_TOKEN",
            "SENTRY_DSN",
        }
        env = event["contexts"]["env"]
        for key in env_keys_to_redact:
            if key in env:
                env[key] = "[REDACTED]"

    return event


def _breadcrumb_filter(crumb: Dict[str, Any], _hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Filter noisy breadcrumbs to reduce event volume.

    Drops:
    - Health check requests (GET /health, /ready)
    - Metrics requests (GET /metrics)

    Preserves:
    - Errors and important events

    Args:
        crumb: Breadcrumb dictionary
        _hint: Additional context - unused but required by API

    Returns:
        Breadcrumb (or None to drop)
    """
    if crumb["category"] == "http.client":
        url = crumb.get("data", {}).get("url", "")
        # Skip noisy health/ready/metrics endpoints
        if any(endpoint in url for endpoint in ["/health", "/ready", "/metrics"]):
            return None
    return crumb


def init_sentry(sentry_dsn: Optional[str], app_mode: str) -> None:
    """Initialize Sentry SDK for error tracking.

    Only initializes if SENTRY_DSN is provided (makes Sentry optional).
    Configures Flask integration, redaction, async transport, and sampling
    to minimize impact on Raspberry Pi resources.

    Args:
        sentry_dsn: Sentry DSN URL (from environment). If None or empty,
            Sentry is disabled.
        app_mode: Application mode (webcam or management) for context tags.

    Example:
        >>> init_sentry(
        ...     sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
        ...     app_mode="webcam"
        ... )
    """
    if not sentry_dsn:
        # Sentry disabled when DSN not provided
        return

    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FlaskIntegration(
                transaction_style="endpoint",
            ),
        ],
        # Set sample rate to reduce volume on Pi
        # ~10% of events sampled to capture errors while avoiding noise
        traces_sample_rate=0.1,
        # Enable to see what's being sent during debugging
        debug=False,
        # Use async transport to avoid blocking request handling
        # Sends events in background thread with queue
        transport="asyncio",
        # Before send hook to redact sensitive data
        before_send=_redact_auth_data,
        # Breadcrumb filter to skip noisy endpoints
        before_breadcrumb=_breadcrumb_filter,
        # Set app_mode as default tag for all events
        tags={
            "app_mode": app_mode,
        },
        # Don't send default PII (browser, IPs, email, etc.)
        send_default_pii=False,
        # Environment detection from app_mode
        environment="production" if app_mode == "management" else "edge",
    )
