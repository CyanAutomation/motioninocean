#!/usr/bin/env python3
"""
Docker healthcheck script.
Checks if the Flask application is responding on port 8000.

Optional environment variables:
  - HEALTHCHECK_URL (default: http://127.0.0.1:8000/health)
  - HEALTHCHECK_READY (default: false; if true, uses /ready instead of /health)
  - HEALTHCHECK_TIMEOUT (default: 5 seconds)
"""

import ipaddress
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse


DEFAULT_HEALTHCHECK_HOST = "http://127.0.0.1:8000"
DEFAULT_HEALTHCHECK_PATH = "/health"
DEFAULT_HEALTHCHECK_TIMEOUT = 5


def _is_public_address(address):
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return (
        ip.is_global
        and not ip.is_private
        and not ip.is_loopback
        and not ip.is_link_local
        and not ip.is_multicast
        and not ip.is_reserved
    )


def check_health():
    """Check if the application is healthy."""
    env_healthcheck_url = os.getenv("HEALTHCHECK_URL")
    healthcheck_ready = os.getenv("HEALTHCHECK_READY", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    healthcheck_path = "/ready" if healthcheck_ready else DEFAULT_HEALTHCHECK_PATH
    default_healthcheck_url = f"{DEFAULT_HEALTHCHECK_HOST}{healthcheck_path}"
    healthcheck_url = env_healthcheck_url or default_healthcheck_url
    if env_healthcheck_url:
        parsed_url = urlparse(env_healthcheck_url)
        hostname = parsed_url.hostname
        normalized_hostname = hostname.strip(".").lower() if hostname else ""
        literal_address = None
        if hostname:
            try:
                literal_address = ipaddress.ip_address(hostname)
            except ValueError:
                literal_address = None
            # Validate hostname format without DNS resolution to prevent TOCTOU attacks
            if not all(c.isalnum() or c in ".-" for c in hostname):
                literal_address = "invalid"  # Force validation failure
        if (
            parsed_url.scheme not in {"http", "https"}
            or not hostname
            or normalized_hostname
            in {
                "localhost",
                "127.0.0.1",
                "0.0.0.0",
                "::1",
                "metadata.google.internal",
                "169.254.169.254",
            }
            or (
                literal_address
                and (literal_address == "invalid" or not _is_public_address(str(literal_address)))
            )
        ):
            healthcheck_url = default_healthcheck_url
    try:
        timeout_seconds = float(os.getenv("HEALTHCHECK_TIMEOUT") or DEFAULT_HEALTHCHECK_TIMEOUT)
    except ValueError:
        timeout_seconds = DEFAULT_HEALTHCHECK_TIMEOUT
    try:
        with urllib.request.urlopen(healthcheck_url, timeout=timeout_seconds) as response:
            if response.status == 200:
                return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        pass
    return False


if __name__ == "__main__":
    sys.exit(0 if check_health() else 1)
