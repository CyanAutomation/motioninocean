"""Application logging configuration helpers."""

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


try:
    import picamera2  # type: ignore[import-not-found]
except (ModuleNotFoundError, ImportError):
    picamera2 = None  # type: ignore[assignment]


DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "text"


class ISO8601Formatter(logging.Formatter):
    """Formatter with ISO-8601 timestamps."""

    def format_time(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
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
            "timestamp": self.format_time(record),
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
            template = (
                "%(asctime)s %(levelname)s %(name)s [pid=%(process)d tid=%(thread)d]: %(message)s"
            )
        super().__init__(fmt=template)


def _parse_bool(raw_value: Optional[str]) -> bool:
    if raw_value is None:
        return False
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def configure_logging() -> None:
    """Configure root logging from environment variables.

    Supported env vars:
    - MIO_LOG_LEVEL: Python logging level (default: INFO)
    - MIO_LOG_FORMAT: text|json (default: text)
    - MIO_LOG_INCLUDE_IDENTIFIERS: true/false for process/thread ids (default: false)
    """

    raw_level = (os.environ.get("MIO_LOG_LEVEL") or DEFAULT_LOG_LEVEL).strip().upper()
    level = getattr(logging, raw_level, logging.INFO)

    log_format = (os.environ.get("MIO_LOG_FORMAT") or DEFAULT_LOG_FORMAT).strip().lower()
    include_identifiers = _parse_bool(os.environ.get("MIO_LOG_INCLUDE_IDENTIFIERS", "false"))

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

    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.handlers.clear()
    werkzeug_logger.propagate = True
    werkzeug_logger.setLevel(level)


def log_provenance_info() -> None:
    """Log camera stack provenance information at application startup.

    Captures and logs:
    - Application version from /app/VERSION file
    - Build suite parameters from /app/BUILD_METADATA
    - libcamera version (from libcamera-hello utility)
    - picamera2 module information and import path
    - Package origins and versions (dpkg for camera packages)
    - Apt pinning preferences for camera packages

    INFO level: Concise single-line summary for standard logging
    DEBUG level: Detailed module inspection, filesystem paths, full version tree, and dpkg output
    """
    logger = logging.getLogger(__name__)

    # Read VERSION file if available
    version_file = "/app/VERSION"
    app_version = "unknown"
    if Path(version_file).exists():
        try:
            with Path(version_file).open(encoding="utf-8") as f:
                app_version = f.read().strip()
        except Exception as e:
            logger.warning("Failed to read VERSION file: %s", e)

    # Read BUILD_METADATA if available
    build_metadata: Dict[str, str] = {}
    metadata_file = "/app/BUILD_METADATA"
    if Path(metadata_file).exists():
        try:
            with Path(metadata_file).open(encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if line and "=" in line:
                        key, value = line.split("=", 1)
                        build_metadata[key] = value
        except Exception as e:
            logger.warning("Failed to read BUILD_METADATA file: %s", e)

    # Capture libcamera version
    libcamera_version = "unknown"
    try:
        result = subprocess.run(
            ["libcamera-hello", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            # Output format: "libcamera 0.6.0 ..."
            version_line = result.stdout.strip().split("\n")[0]
            libcamera_version = version_line.strip()
    except Exception as e:
        logger.debug("Could not capture libcamera version: %s", e)

    # Capture picamera2 module info
    picamera2_version = "unknown"
    picamera2_path = "unknown"
    try:
        if picamera2 is not None:
            picamera2_path = picamera2.__file__
            picamera2_version = getattr(picamera2, "__version__", "unknown")
    except Exception as e:
        logger.debug("Could not import picamera2: %s", e)

    # Get dpkg info for camera packages
    dpkg_info: Dict[str, Dict[str, str]] = {}
    try:
        result = subprocess.run(
            [
                "dpkg-query",
                "-W",
                "-f=${Package}\t${Version}\t${Origin}\n",
                "libcamera-apps",
                "python3-picamera2",
                "python3-libcamera",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line and "\t" in line:
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        pkg_name = parts[0]
                        dpkg_info[pkg_name] = {
                            "version": parts[1],
                            "origin": parts[2],
                        }
    except Exception as e:
        logger.debug("Could not query dpkg for package origins: %s", e)

    # Get apt preferences info
    apt_prefs_content = "not found"
    preferences_file = "/etc/apt/preferences.d/rpi-camera.preferences"
    if Path(preferences_file).exists():
        try:
            with Path(preferences_file).open(encoding="utf-8") as f:
                apt_prefs_content = f.read()
        except Exception as e:
            logger.debug("Could not read apt preferences: %s", e)

    # Build INFO-level summary (single line)
    debian_suite = build_metadata.get("DEBIAN_SUITE", "unknown")
    rpi_suite = build_metadata.get("RPI_SUITE", "unknown")
    include_mock = build_metadata.get("INCLUDE_MOCK_CAMERA", "unknown")
    build_time = build_metadata.get("BUILD_TIMESTAMP", "unknown")

    # Extract origin summary from dpkg_info
    origins = [info.get("origin", "unknown") for info in dpkg_info.values()]
    origin_summary = "/".join(set(origins)) if origins else "unknown"

    info_summary = (
        f"version={app_version} libcamera={libcamera_version} picamera2={picamera2_version} "
        f"debian:suite={debian_suite} rpi:suite={rpi_suite} mock_camera={include_mock} "
        f"package_origins={origin_summary}"
    )
    logger.info("Camera stack provenance: %s", info_summary)

    # Log DEBUG-level detailed inspection
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("BUILD_METADATA: %s", build_metadata)
        logger.debug("picamera2.__file__: %s", picamera2_path)
        logger.debug("Full libcamera version: %s", libcamera_version)
        logger.debug("Package versions and origins: %s", dpkg_info)
        logger.debug(
            "Apt preferences file (/etc/apt/preferences.d/rpi-camera.preferences):\n%s",
            apt_prefs_content,
        )
        logger.debug(
            "Provenance snapshot: %s",
            {
                "app_version": app_version,
                "libcamera_version": libcamera_version,
                "picamera2_version": picamera2_version,
                "picamera2_path": picamera2_path,
                "package_info": dpkg_info,
                "debian_suite": debian_suite,
                "rpi_suite": rpi_suite,
                "mock_camera_enabled": include_mock,
                "build_timestamp": build_time,
                "package_origins": origin_summary,
            },
        )
