"""Tests for the built-in process-local rate limiter."""

import builtins
from concurrent.futures import ThreadPoolExecutor

import pytest
from flask import Flask

from pi_camera_in_docker.rate_limiter import InMemoryRateLimiter, create_rate_limiter


def test_rate_limiter_enforces_route_limits_and_retry_after():
    """The configured route limit returns 429 with a retry delay after its quota."""
    now = [100.0]
    app = Flask(__name__)
    limiter = InMemoryRateLimiter(app, clock=lambda: now[0])

    @app.get("/limited")
    @limiter.limit("2/second")
    def limited():
        return "ok"

    client = app.test_client()
    assert client.get("/limited").status_code == 200
    assert client.get("/limited").status_code == 200
    blocked = client.get("/limited")
    assert blocked.status_code == 429
    assert blocked.headers.get("Retry-After") == "1"

    now[0] = 101.01
    assert client.get("/limited").status_code == 200


def test_rate_limiter_enforces_each_window_atomically():
    """A long window still applies after the short burst window expires."""
    now = [50.0]
    app = Flask(__name__)
    limiter = InMemoryRateLimiter(app, clock=lambda: now[0])

    @app.get("/limited")
    @limiter.limit("2/second;3/minute")
    def limited():
        return "ok"

    client = app.test_client()
    assert [client.get("/limited").status_code for _ in range(2)] == [200, 200]
    assert client.get("/limited").status_code == 429
    now[0] = 51.01
    assert client.get("/limited").status_code == 200
    assert client.get("/limited").status_code == 429


def test_rate_limiter_checks_concurrent_requests_atomically():
    """Only one simultaneous request consumes the final available quota slot."""
    app = Flask(__name__)
    limiter = InMemoryRateLimiter(app)

    @app.get("/limited")
    @limiter.limit("1/second")
    def limited():
        return "ok"

    def request_once():
        with app.test_client() as client:
            return client.get("/limited").status_code

    with ThreadPoolExecutor(max_workers=12) as executor:
        statuses = list(executor.map(lambda _index: request_once(), range(12)))

    assert statuses.count(200) == 1
    assert statuses.count(429) == 11


def test_rate_limiter_applies_default_limit_to_unannotated_routes():
    """Unannotated routes receive the configured app-wide default per endpoint."""
    app = Flask(__name__)
    limiter = InMemoryRateLimiter(app, default_limits=["1/minute"])

    @app.get("/one")
    def one():
        return "one"

    @app.get("/two")
    def two():
        return "two"

    client = app.test_client()
    assert client.get("/one").status_code == 200
    assert client.get("/one").status_code == 429
    assert client.get("/two").status_code == 200


def test_rate_limiter_exemption_skips_the_route_bucket():
    """A true exemption predicate bypasses that decorator's quota."""
    app = Flask(__name__)
    limiter = InMemoryRateLimiter(app)

    @app.get("/limited")
    @limiter.limit("1/minute", exempt_when=lambda: True)
    def limited():
        return "ok"

    client = app.test_client()
    assert client.get("/limited").status_code == 200
    assert client.get("/limited").status_code == 200


def test_default_rate_limiter_does_not_import_flask_limiter(monkeypatch):
    """The default in-process backend works without the optional extension."""
    app = Flask(__name__)
    original_import = builtins.__import__

    def reject_optional_limiter(name, *args, **kwargs):
        if name == "flask_limiter" or name.startswith("flask_limiter."):
            raise ImportError("optional limiter is not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_optional_limiter)

    limiter = create_rate_limiter(app, default_limits=["1/minute"])

    assert isinstance(limiter, InMemoryRateLimiter)


def test_external_rate_limiter_backend_reports_optional_dependency(monkeypatch):
    """A non-memory backend explains which optional package is needed."""
    app = Flask(__name__)
    original_import = builtins.__import__

    def reject_optional_limiter(name, *args, **kwargs):
        if name == "flask_limiter" or name.startswith("flask_limiter."):
            raise ImportError("optional limiter is not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_optional_limiter)

    with pytest.raises(RuntimeError, match=r"requirements-rate-limiter\.txt"):
        create_rate_limiter(app, storage_uri="redis://localhost:6379/0")
