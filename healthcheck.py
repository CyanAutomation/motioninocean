#!/usr/bin/env python3
"""
Docker healthcheck script.
Checks if the Flask application is responding on port 8000.

Optional environment variables:
  - HEALTHCHECK_URL (default: http://127.0.0.1:8000/health)
  - HEALTHCHECK_TIMEOUT (default: 5 seconds)
"""

import os
import sys
import ipaddress
import urllib.error
import urllib.request
from urllib.parse import urlparse


DEFAULT_HEALTHCHECK_URL = "http://127.0.0.1:8000/health"
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


def _is_allowed_url(url):
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"}:
        return False

    hostname = parsed_url.hostname
    if not hostname:
        return False

    normalized_hostname = hostname.strip(".").lower()
    if normalized_hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        return False

    try:
        literal_address = ipaddress.ip_address(hostname)
    except ValueError:
        literal_address = None

    if literal_address:
        return _is_public_address(str(literal_address))

    # Validate hostname format without DNS resolution to prevent TOCTOU attacks
    if not all(c.isalnum() or c in ".-" for c in hostname):
        return False

    # Block common internal hostnames
    if normalized_hostname in {"localhost", "metadata.google.internal", "169.254.169.254"}:
        return False

    return True


def check_health():
    """Check if the application is healthy."""
    env_healthcheck_url = os.getenv("HEALTHCHECK_URL")
    healthcheck_url = env_healthcheck_url or DEFAULT_HEALTHCHECK_URL
    if env_healthcheck_url and not _is_allowed_url(env_healthcheck_url):
        print(
            f"Warning: Invalid HEALTHCHECK_URL '{env_healthcheck_url}', using default",
            file=sys.stderr,
        )
        healthcheck_url = DEFAULT_HEALTHCHECK_URL
    timeout_value = os.getenv("HEALTHCHECK_TIMEOUT")
    if not timeout_value:
        timeout_seconds = DEFAULT_HEALTHCHECK_TIMEOUT
    else:
        try:
            timeout_seconds = float(timeout_value)
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
