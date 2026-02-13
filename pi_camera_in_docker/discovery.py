import hashlib
import json
import logging
import random
import socket
import urllib.error
import urllib.request
import uuid
from threading import Event, Thread
from typing import Any, Dict, Optional
from urllib.parse import urlsplit, urlunsplit


logger = logging.getLogger(__name__)


def _stable_node_id(hostname: str) -> str:
    mac = f"{uuid.getnode():012x}"
    digest = hashlib.sha256(f"{hostname}-{mac}".encode()).hexdigest()
    return f"node-{digest[:16]}"


def _safe_management_url(management_url: str) -> str:
    parts = urlsplit(management_url)
    host = parts.hostname or ""
    if parts.port is not None:
        host = f"{host}:{parts.port}"
    base_path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, host, f"{base_path}/api/discovery/announce", "", ""))


def _redacted_url_for_logs(url: str) -> str:
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.port is not None:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, "", ""))


class DiscoveryAnnouncer:
    def __init__(
        self,
        *,
        management_url: str,
        token: str,
        interval_seconds: float,
        node_id: str,
        payload: Dict[str, Any],
        shutdown_event: Event,
    ):
        self.management_url = _safe_management_url(management_url)
        self.management_url_log = _redacted_url_for_logs(self.management_url)
        self.token = token
        self.interval_seconds = max(1.0, float(interval_seconds))
        self.node_id = node_id
        self.payload = payload
        self.shutdown_event = shutdown_event
        self._thread: Optional[Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = Thread(target=self._run_loop, name="discovery-announcer", daemon=True)
        self._thread.start()

    def stop(self, timeout_seconds: float = 3.0) -> None:
        self.shutdown_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout_seconds)

    def _announce_once(self) -> bool:
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
                        "discovery_announce_ok: node_id=%s status=%s endpoint=%s",
                        self.node_id,
                        status_code,
                        self.management_url_log,
                    )
                    return True
                logger.warning(
                    "discovery_announce_failed: node_id=%s status=%s endpoint=%s",
                    self.node_id,
                    status_code,
                    self.management_url_log,
                )
                return False
        except urllib.error.HTTPError as exc:
            logger.warning(
                "discovery_announce_http_error: node_id=%s status=%s endpoint=%s",
                self.node_id,
                exc.code,
                self.management_url_log,
            )
            return False
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning(
                "discovery_announce_network_error: node_id=%s reason=%s endpoint=%s",
                self.node_id,
                str(exc),
                self.management_url_log,
            )
            return False

    def _run_loop(self) -> None:
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
                "discovery_announce_retry_scheduled: node_id=%s failures=%s wait_seconds=%.2f",
                self.node_id,
                failures,
                wait_seconds,
            )


def build_discovery_payload(config: Dict[str, Any]) -> Dict[str, Any]:
    hostname = socket.gethostname() or "unknown-host"
    node_id = config.get("discovery_node_id") or _stable_node_id(hostname)
    base_url = config.get("discovery_base_url", "").rstrip("/")
    if not base_url:
        error_message = "discovery_base_url is required in config"
        raise ValueError(error_message)
    return {
        "node_id": node_id,
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
