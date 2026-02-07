"""Application logging configuration helpers."""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional


DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "text"


class ISO8601Formatter(logging.Formatter):
    """Formatter with ISO-8601 timestamps."""

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc).astimezone()
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat(timespec="milliseconds")


class JSONFormatter(ISO8601Formatter):
    """Structured JSON formatter for container log aggregation."""

    def __init__(self, include_identifiers: bool = False) -> None:
        super().__init__()
        self.include_identifiers = include_identifiers

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if self.include_identifiers:
            payload["process"] = record.process
            payload["thread"] = record.thread

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


class TextFormatter(ISO8601Formatter):
    """Human-readable formatter optimized for docker logs output."""

    def __init__(self, include_identifiers: bool = False) -> None:
        template = "%(asctime)s %(levelname)s %(name)s: %(message)s"
        if include_identifiers:
            template = "%(asctime)s %(levelname)s %(name)s [pid=%(process)d tid=%(thread)d]: %(message)s"
        super().__init__(fmt=template)


def _parse_bool(raw_value: Optional[str]) -> bool:
    if raw_value is None:
        return False
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def configure_logging() -> None:
    """Configure root logging from environment variables.

    Supported env vars:
    - LOG_LEVEL: Python logging level (default: INFO)
    - LOG_FORMAT: text|json (default: text)
    - LOG_INCLUDE_IDENTIFIERS: true/false for process/thread ids (default: false)
    """

    raw_level = (os.environ.get("LOG_LEVEL") or DEFAULT_LOG_LEVEL).strip().upper()
    level = getattr(logging, raw_level, logging.INFO)

    log_format = (os.environ.get("LOG_FORMAT") or DEFAULT_LOG_FORMAT).strip().lower()
    include_identifiers = _parse_bool(os.environ.get("LOG_INCLUDE_IDENTIFIERS", "false"))

    if log_format == "json":
        formatter: logging.Formatter = JSONFormatter(include_identifiers=include_identifiers)
    else:
        formatter = TextFormatter(include_identifiers=include_identifiers)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)
