"""Small process-local request rate limiter with an optional external backend."""

from __future__ import annotations

import logging
import math
import re
import time
from collections import OrderedDict, deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import wraps
from threading import Lock
from typing import Any, Protocol, TypeVar, cast

from flask import Flask, current_app, jsonify, request


logger = logging.getLogger(__name__)
_LIMIT_PATTERN = re.compile(r"^(?P<count>[1-9][0-9]*)/(?P<period>second|minute|hour|day)s?$", re.I)
_PERIOD_SECONDS = {"second": 1.0, "minute": 60.0, "hour": 3600.0, "day": 86400.0}
_MAX_BUCKETS = 10_000

F = TypeVar("F", bound=Callable[..., Any])


class RateLimitConfigurationError(ValueError):
    """Raised when a configured rate limit uses unsupported syntax."""


@dataclass(frozen=True)
class _Rate:
    """One request quota and its sliding time window."""

    count: int
    window_seconds: float


class RateLimiterProtocol(Protocol):
    """Decorator interface shared by the built-in and optional limiters."""

    def limit(
        self,
        limit_value: str,
        *,
        exempt_when: Callable[[], bool] | None = None,
    ) -> Callable[[F], F]:
        """Decorate a Flask view with one or more request limits."""


def get_remote_address() -> str:
    """Return the direct peer address for the active Flask request.

    Returns:
        The request's remote address, or a stable local fallback when absent.
    """
    return request.remote_addr or "127.0.0.1"


def _parse_limits(limit_value: str) -> tuple[_Rate, ...]:
    """Parse the subset of Flask-Limiter syntax used by this application."""
    limits: list[_Rate] = []
    for raw_limit in limit_value.split(";"):
        match = _LIMIT_PATTERN.fullmatch(raw_limit.strip())
        if match is None:
            message = f"Unsupported rate limit {raw_limit!r}"
            raise RateLimitConfigurationError(message)
        period = match.group("period").lower().rstrip("s")
        limits.append(
            _Rate(
                count=int(match.group("count")),
                window_seconds=_PERIOD_SECONDS[period],
            )
        )
    if not limits:
        message = "At least one rate limit is required"
        raise RateLimitConfigurationError(message)
    return tuple(limits)


class InMemoryRateLimiter:
    """Enforce per-client sliding-window quotas inside one application process.

    The default implementation is suitable for the project's one-process,
    threaded WSGI server. Limits are synchronized across request threads and
    bounded to avoid unbounded memory growth from many distinct client addresses.
    """

    def __init__(
        self,
        app: Flask | None = None,
        *,
        key_func: Callable[[], str] = get_remote_address,
        default_limits: Iterable[str] = (),
        clock: Callable[[], float] = time.monotonic,
        max_buckets: int = _MAX_BUCKETS,
    ) -> None:
        """Create a process-local limiter and optionally attach its default rule.

        Args:
            app: Flask app to attach default limits to, if provided.
            key_func: Function that returns a client's rate-limit identity.
            default_limits: Limits applied to routes without explicit decorators.
            clock: Monotonic clock function, replaceable for deterministic tests.
            max_buckets: Maximum number of client, route, and window counters kept.
        """
        self._key_func = key_func
        self._clock = clock
        self._max_buckets = max(1, max_buckets)
        self._default_limits = tuple(
            rate for value in default_limits for rate in _parse_limits(value)
        )
        self._lock = Lock()
        self._windows: OrderedDict[tuple[str, str, _Rate], deque[float]] = OrderedDict()
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Register the app-wide default limit hook.

        Args:
            app: Flask application to protect.
        """

        @app.before_request
        def _enforce_default_limit() -> tuple[Any, int, dict[str, str]] | None:
            if not self._default_limits:
                return None
            view = current_app.view_functions.get(request.endpoint or "")
            if getattr(view, "_mio_explicit_limits", False):
                return None
            retry_after = self._check(
                self._key_func(),
                request.endpoint or request.path,
                self._default_limits,
            )
            return self._limited_response(retry_after) if retry_after else None

    def limit(
        self,
        limit_value: str,
        *,
        exempt_when: Callable[[], bool] | None = None,
    ) -> Callable[[F], F]:
        """Decorate a Flask view with one or more sliding-window limits.

        Args:
            limit_value: Semicolon-separated limits such as ``10/second;120/minute``.
            exempt_when: Optional request predicate that skips these limits when true.

        Returns:
            A decorator that enforces the parsed limits before calling the view.

        Raises:
            ValueError: If a limit uses syntax this implementation does not support.
        """
        limits = _parse_limits(limit_value)

        def decorator(function: F) -> F:
            scope = f"{function.__module__}.{function.__qualname__}:{limit_value}"

            @wraps(function)
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                if exempt_when is None or not exempt_when():
                    retry_after = self._check(self._key_func(), scope, limits)
                    if retry_after:
                        return self._limited_response(retry_after)
                return function(*args, **kwargs)

            setattr(wrapped, "_mio_explicit_limits", True)  # noqa: B010 - runtime marker
            return cast("F", wrapped)

        return decorator

    def _check(self, client: str, scope: str, limits: tuple[_Rate, ...]) -> float:
        """Atomically check and record a request against each configured window."""
        now = self._clock()
        keys = [(client, scope, rate) for rate in limits]
        retry_after = 0.0
        with self._lock:
            buckets: list[tuple[tuple[str, str, _Rate], deque[float]]] = []
            for key in keys:
                rate = key[2]
                bucket = self._windows.setdefault(key, deque())
                while bucket and now - bucket[0] >= rate.window_seconds:
                    bucket.popleft()
                self._windows.move_to_end(key)
                buckets.append((key, bucket))
                if len(bucket) >= rate.count:
                    retry_after = max(
                        retry_after,
                        rate.window_seconds - (now - bucket[0]),
                    )

            if retry_after > 0:
                for key, bucket in buckets:
                    if not bucket:
                        self._windows.pop(key, None)
                return retry_after

            for _key, bucket in buckets:
                bucket.append(now)
            while len(self._windows) > self._max_buckets:
                self._windows.popitem(last=False)
        return 0.0

    @staticmethod
    def _limited_response(retry_after: float) -> tuple[Any, int, dict[str, str]]:
        """Build a JSON 429 response with a useful retry delay."""
        return (
            jsonify({"error": "RATE_LIMITED", "message": "Request rate limit exceeded"}),
            429,
            {"Retry-After": str(max(1, math.ceil(retry_after)))},
        )


def create_rate_limiter(
    app: Flask,
    *,
    key_func: Callable[[], str] = get_remote_address,
    default_limits: Iterable[str] = (),
    storage_uri: str = "memory://",
) -> RateLimiterProtocol:
    """Use in-house memory limits by default and load external storage on demand.

    Args:
        app: Flask application to protect.
        key_func: Function that returns a client's rate-limit identity.
        default_limits: Limits applied to routes without explicit decorators.
        storage_uri: ``memory://`` or a Flask-Limiter storage URI.

    Returns:
        A limiter implementing the route decorator interface.

    Raises:
        RuntimeError: If an external storage URI is requested without the optional
            Flask-Limiter package installed.
    """
    if storage_uri.strip().lower() in {"memory", "memory://"}:
        return InMemoryRateLimiter(
            app,
            key_func=key_func,
            default_limits=default_limits,
        )

    try:
        from flask_limiter import Limiter as FlaskLimiter  # noqa: PLC0415 - optional package
        from flask_limiter.util import (  # noqa: PLC0415 - optional package
            get_remote_address as flask_remote_address,
        )
    except ImportError as exc:
        message = (
            "A non-memory MIO_LIMITER_STORAGE_URI requires the optional "
            "requirements-rate-limiter.txt package"
        )
        raise RuntimeError(message) from exc

    logger.info("Using optional Flask-Limiter backend for storage URI")
    limiter = FlaskLimiter(
        app=app,
        key_func=flask_remote_address if key_func is get_remote_address else key_func,
        default_limits=list(default_limits),
        storage_uri=storage_uri,
    )
    return cast("RateLimiterProtocol", limiter)
