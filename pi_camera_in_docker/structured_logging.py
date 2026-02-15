"""Structured logging utilities for correlation tracking and event logging."""

import json
import logging
import uuid
from typing import Any, Optional

from flask import g, request


logger = logging.getLogger(__name__)


def get_correlation_id() -> str:
    """Get or create correlation ID for current request."""
    if not hasattr(g, "correlation_id"):
        # Try to get from request header, or generate new one
        g.correlation_id = request.headers.get("X-Correlation-ID", uuid.uuid4().hex)
    return g.correlation_id


def log_event(
    event_type: str,
    severity: str = "INFO",
    **context: Any,
) -> None:
    """Log a structured event with correlation ID and context.

    Args:
        event_type: Name of the event (e.g., "node_approved", "announcement_sent")
        severity: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        **context: Additional context fields to include in the event
    """
    try:
        correlation_id = get_correlation_id()
    except RuntimeError:
        # Outside request context
        correlation_id = "none"

    event_payload = {
        "event_type": event_type,
        "correlation_id": correlation_id,
        **context,
    }

    level = getattr(logging, severity.upper(), logging.INFO)
    logger.log(level, "event=%s %s", event_type, json.dumps(event_payload, default=str))


def log_error(
    operation: str,
    error_type: str,
    message: str,
    resource_id: Optional[str] = None,
    severity: str = "ERROR",
    **context: Any,
) -> None:
    """Log a structured error with full context.

    Args:
        operation: The operation being performed (e.g., "node_request", "announcement_send")
        error_type: Category of error (e.g., "timeout", "auth_failed", "network_error")
        message: Human-readable error message
        resource_id: Optional resource ID affecting this error (node_id, etc.)
        severity: Log level
        **context: Additional context fields
    """
    try:
        correlation_id = get_correlation_id()
    except RuntimeError:
        correlation_id = "none"

    error_payload = {
        "operation": operation,
        "error_type": error_type,
        "correlation_id": correlation_id,
        "message": message,
    }

    if resource_id:
        error_payload["resource_id"] = resource_id

    error_payload.update(context)

    level = getattr(logging, severity.upper(), logging.ERROR)
    logger.log(
        level,
        "error operation=%s type=%s %s",
        operation,
        error_type,
        json.dumps(error_payload, default=str),
    )
