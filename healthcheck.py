#!/usr/bin/env python3
"""
Docker healthcheck script.
Checks if the Flask application is responding on port 8000.
"""

import sys
import urllib.error
import urllib.request


def check_health():
    """Check if the application is healthy."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5) as response:
            if response.status == 200:
                return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        pass
    return False


if __name__ == "__main__":
    sys.exit(0 if check_health() else 1)
