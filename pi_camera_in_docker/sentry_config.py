"""Sentry error tracking initialization and configuration.

Provides optional error tracking integration when MIO_SENTRY_DSN environment
variable is set. Includes data filtering to redact sensitive auth tokens
while preserving useful debugging context.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


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
            "MIO_WEBCAM_CONTROL_PLANE_AUTH_TOKEN",
            "MIO_MANAGEMENT_AUTH_TOKEN",
            "MIO_DISCOVERY_TOKEN",
            "MIO_SENTRY_DSN",
            # Legacy aliases retained during migration window
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


def _get_app_version() -> str:
    """Read the application version from /app/VERSION.

    Falls back to "unknown" when the file is absent (dev environments, tests).

    Returns:
        Version string (e.g. "1.2.3") or "unknown".
    """
    version_file = Path("/app/VERSION")
    if version_file.exists():
        try:
            return version_file.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return "unknown"


def _traces_sampler(sampling_context: Dict[str, Any]) -> float:
    """Determine traces sample rate per transaction.

    Applies per-route sampling so that high-frequency noise endpoints
    do not consume Sentry quota, while mutations are always captured.

    Sample rates:
    - /stream, /stream.mjpg, /webcam, /webcam/ → 0.0
      (infinite MJPEG response/compat aliases, never sample)
    - /health, /ready, /metrics → 0.0 (polling noise)
    - PATCH / POST / DELETE     → 1.0 (always capture mutations and actions)
    - Everything else           → 0.1 (10% of read traffic)

    Args:
        sampling_context: Sentry-provided context dict; may include
            ``wsgi_environ`` with PATH_INFO and REQUEST_METHOD.

    Returns:
        Float between 0.0 (never) and 1.0 (always).
    """
    wsgi_environ = sampling_context.get("wsgi_environ", {})
    path = wsgi_environ.get("PATH_INFO", "")
    method = wsgi_environ.get("REQUEST_METHOD", "GET")

    stream_paths = {"/stream", "/stream.mjpg", "/webcam", "/webcam/"}

    # Never sample infinite-duration MJPEG stream routes — would pin a Sentry envelope open.
    if path in stream_paths:
        return 0.0

    # Never sample high-frequency polling noise.
    if path in {"/health", "/ready", "/metrics"}:
        return 0.0

    # Always sample mutations and triggered actions (low volume, high diagnostic value).
    if method in {"PATCH", "POST", "DELETE"}:
        return 1.0

    # Default: 10% of remaining read traffic.
    return 0.1


def init_sentry(sentry_dsn: Optional[str], app_mode: str) -> None:
    """Initialize Sentry SDK for error tracking.

    Only initializes if MIO_SENTRY_DSN is provided (makes Sentry optional).
    Configures Flask integration, explicit logging integration, per-route trace
    sampling, release tagging, and redaction hooks to minimize impact on
    Raspberry Pi resources.

    Args:
        sentry_dsn: Sentry DSN URL (from MIO_SENTRY_DSN env var). If None or
            empty, Sentry is disabled.
        app_mode: Application mode (webcam or management) for context tags.
            Webcam nodes are tagged environment="edge"; management hub is
            tagged environment="production".

    Example:
        >>> init_sentry(
        ...     sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
        ...     app_mode="webcam"
        ... )
    """
    if not sentry_dsn:
        # Sentry disabled when DSN not provided
        return

    sentry_sdk.init(  # type: ignore[call-arg]
        dsn=sentry_dsn,
        integrations=[
            FlaskIntegration(
                transaction_style="endpoint",
            ),
            # Explicitly configure logging bridge so WARNING+ lines produce
            # breadcrumbs and ERROR+ lines produce Sentry events.  Without
            # this the SDK passive default could silently change on upgrade.
            LoggingIntegration(
                level=logging.WARNING,
                event_level=logging.ERROR,
            ),
        ],
        # Per-route sampler: never traces stream routes (/stream, /stream.mjpg, /webcam)
        # or health polling;
        # always traces mutations; 10% of remaining read traffic.
        traces_sampler=_traces_sampler,
        # Release tag enables regression detection and suspect-commit linking.
        release=_get_app_version(),
        # Enable to see what's being sent during debugging
        debug=False,
        # Before send hook to redact sensitive data
        before_send=_redact_auth_data,  # type: ignore[arg-type]
        # Breadcrumb filter to skip noisy endpoints
        before_breadcrumb=_breadcrumb_filter,
        # Don't send default PII (browser, IPs, email, etc.)
        send_default_pii=False,
        # Environment detection from app_mode
        environment="production" if app_mode == "management" else "edge",
    )

    # Tag events with current application mode for easier filtering.
    sentry_sdk.set_tag("app_mode", app_mode)
