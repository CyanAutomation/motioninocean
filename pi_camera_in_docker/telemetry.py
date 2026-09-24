"""Optional Sentry adapter with no-op behavior when its SDK is not installed."""

from __future__ import annotations

from contextlib import contextmanager
from importlib import import_module
from typing import TYPE_CHECKING, Any, Iterator


if TYPE_CHECKING:
    from types import ModuleType


class _NullScope:
    """Scope-compatible no-op used by installations without Sentry."""

    def set_tag(self, _key: str, _value: Any) -> None:
        """Accept a tag without storing it."""

    def set_context(self, _key: str, _value: Any) -> None:
        """Accept context without storing it."""

    def capture_exception(self, _error: BaseException) -> None:
        """Ignore SDK capture requests when Sentry is not installed."""


def _get_sentry_sdk() -> ModuleType | None:
    """Import the optional Sentry SDK when it is available.

    Returns:
        The Sentry SDK module, or None when it is not installed.
    """
    try:
        module = import_module("sentry_sdk")
    except ImportError:
        return None
    else:
        return module


@contextmanager
def new_scope() -> Iterator[Any]:
    """Return a Sentry scope or a no-op scope for optional telemetry calls.

    Yields:
        A scope with ``set_tag``, ``set_context``, and ``capture_exception`` methods.
    """
    sdk = _get_sentry_sdk()
    if sdk is None:
        yield _NullScope()
    else:
        with sdk.new_scope() as scope:
            yield scope


def get_current_scope() -> Any:
    """Return the active Sentry scope, or a no-op scope when unavailable.

    Returns:
        Active SDK scope or a no-op scope.
    """
    sdk = _get_sentry_sdk()
    return sdk.get_current_scope() if sdk is not None else _NullScope()


def capture_exception(error: BaseException) -> None:
    """Forward an exception to Sentry when installed, otherwise rely on logs.

    Args:
        error: Exception to forward to the configured Sentry SDK.
    """
    sdk = _get_sentry_sdk()
    if sdk is not None:
        sdk.capture_exception(error)
