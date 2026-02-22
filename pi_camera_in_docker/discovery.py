"""Discovery and self-registration protocol for Motion In Ocean webcam nodes.

Implements automatic webcam discovery where webcam nodes periodically announce
their availability to a management hub. Includes exponential backoff retry logic,
secure HTTP request handling, and graceful shutdown.
"""

import hashlib
import json
import logging
import random
import socket
import urllib.error
import urllib.request
import uuid
from threading import Event, Lock, Thread
from typing import Any, Dict, Optional
from urllib.parse import urlsplit, urlunsplit

import sentry_sdk

logger = logging.getLogger(__name__)


def _stable_webcam_id(hostname: str) -> str:
    """Generate stable webcam ID based on hostname and MAC address.

    Args:
        hostname: System hostname.

    Returns:
        Stable webcam ID string (consistent across restarts).
    """
    mac = f"{uuid.getnode():012x}"
    digest = hashlib.sha256(f"{hostname}-{mac}".encode()).hexdigest()
    return f"node-{digest[:16]}"


def _safe_management_url(management_url: str) -> str:
    """Build safe management hub discovery endpoint URL.

    Args:
        management_url: Management hub base URL.

    Returns:
        Full URL to /api/discovery/announce endpoint.
    """
    parts = urlsplit(management_url)
    host = parts.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if parts.port is not None:
        host = f"{host}:{parts.port}"
    normalized_path = parts.path.rstrip("/")
    announce_path = "/api/discovery/announce"

    if normalized_path.endswith(announce_path):
        safe_path = normalized_path
    elif normalized_path:
        safe_path = f"{normalized_path}{announce_path}"
    else:
        safe_path = announce_path

    return urlunsplit((parts.scheme, host, safe_path, "", ""))


def _redacted_url_for_logs(url: str) -> str:
    """Redact query parameters and fragments from URL for safe logging.

    Args:
        url: Full URL to redact.

    Returns:
        URL with only scheme, host, port, and path visible.
    """
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.port is not None:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, "", ""))


class DiscoveryAnnouncer:
    """Daemon thread for periodic self-registration with management hub.

    Announces webcam availability at regular intervals with exponential backoff retry.
    Runs in background thread and stops gracefully on shutdown.
    """

    def __init__(
        self,
        *,
        management_url: str,
        token: str,
        interval_seconds: float,
        webcam_id: str,
        payload: Dict[str, Any],
        shutdown_event: Event,
    ):
        """Initialize discovery announcer.

        Args:
            management_url: Management hub base URL.
            token: Bearer token for discovery announcement authentication.
            interval_seconds: Seconds between announcements (minimum 1.0).
            webcam_id: Node identifier.
            payload: Node registration payload dict.
            shutdown_event: Threading event to signal shutdown.
        """
        self.management_url = _safe_management_url(management_url)
        self.management_url_log = _redacted_url_for_logs(self.management_url)
        self.token = token
        self.interval_seconds = max(1.0, float(interval_seconds))
        self.webcam_id = webcam_id
        self.payload = payload
        self.shutdown_event = shutdown_event
        self._thread: Optional[Thread] = None
        self._thread_lock = Lock()

    def start(self) -> None:
        """Start the discovery announcement daemon thread.

        Safe to call multiple times (idempotent) and restart-safe after ``stop()``.
        """
        with self._thread_lock:
            if self._thread and self._thread.is_alive():
                return
            self.shutdown_event.clear()
            self._thread = Thread(target=self._run_loop, name="discovery-announcer", daemon=True)
            self._thread.start()

    def stop(self, timeout_seconds: float = 3.0) -> None:
        """Stop the discovery announcement daemon thread gracefully.

        Args:
            timeout_seconds: Maximum time to wait for thread termination.
        """
        with self._thread_lock:
            self.shutdown_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=timeout_seconds)
            if self._thread and not self._thread.is_alive():
                self._thread = None

    def _announce_once(self) -> bool:
        """Attempt a single announcement to management hub.

        Returns:
            True on success (HTTP 200/201), False on any error.
        """
        body = json.dumps(self.payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        request = urllib.request.Request(
            url=self.management_url,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=5.0) as response:
                status_code = getattr(response, "status", 0)
                if status_code in {200, 201}:
                    logger.info(
                        "discovery_announce_ok: webcam_id=%s status=%s endpoint=%s",
                        self.webcam_id,
                        status_code,
                        self.management_url_log,
                    )
                    return True
                logger.warning(
                    "discovery_announce_failed: webcam_id=%s status=%s endpoint=%s",
                    self.webcam_id,
                    status_code,
                    self.management_url_log,
                )
                return False
        except urllib.error.HTTPError as exc:
            logger.warning(
                "discovery_announce_http_error: webcam_id=%s status=%s endpoint=%s",
                self.webcam_id,
                exc.code,
                self.management_url_log,
            )
            with sentry_sdk.new_scope() as scope:
                scope.set_tag("component", "discovery")
                scope.set_tag("webcam_id", self.webcam_id)
                scope.capture_exception(exc)
            return False
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning(
                "discovery_announce_network_error: webcam_id=%s reason=%s endpoint=%s",
                self.webcam_id,
                str(exc),
                self.management_url_log,
            )
            with sentry_sdk.new_scope() as scope:
                scope.set_tag("component", "discovery")
                scope.set_tag("webcam_id", self.webcam_id)
                scope.capture_exception(exc)
            return False

    def _run_loop(self) -> None:
        """Main daemon loop with exponential backoff retry logic.

        Continuously attempts announcements at configured interval.
        On failure, uses exponential backoff up to 300 seconds.
        Exits when shutdown_event is set.
        """
        failures = 0
        wait_seconds = 0.0
        while not self.shutdown_event.wait(wait_seconds):
            success = self._announce_once()
            if success:
                failures = 0
                wait_seconds = self.interval_seconds
                continue

            failures += 1
            backoff_seconds = min(self.interval_seconds * (2 ** min(failures - 1, 5)), 300.0)
            jitter = random.uniform(0.0, min(2.0, backoff_seconds * 0.25))
            wait_seconds = backoff_seconds + jitter
            logger.warning(
                "discovery_announce_retry_scheduled: webcam_id=%s failures=%s wait_seconds=%.2f",
                self.webcam_id,
                failures,
                wait_seconds,
            )


def build_discovery_payload(config: Dict[str, Any]) -> Dict[str, Any]:
    """Build webcam registration payload for discovery announcement.

    Args:
        config: Config dict with discovery_webcam_id and discovery_base_url.

    Returns:
        Node payload dict ready for announcement to management hub.

    Raises:
        ValueError: If discovery_base_url is not set in config.
    """
    hostname = socket.gethostname() or "unknown-host"
    webcam_id = config.get("discovery_webcam_id") or _stable_webcam_id(hostname)
    base_url = config.get("discovery_base_url", "").rstrip("/")
    if not base_url:
        error_message = "discovery_base_url is required in config"
        raise ValueError(error_message)
    return {
        "webcam_id": webcam_id,
        "name": hostname,
        "base_url": base_url,
        "transport": "http",
        "capabilities": ["stream", "snapshot"],
        "labels": {
            "hostname": hostname,
            "device_class": "webcam",
            "app_mode": "webcam",
        },
        "auth": {"type": "none"},
    }
