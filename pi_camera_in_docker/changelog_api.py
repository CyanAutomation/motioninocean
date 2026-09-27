"""Utilities for serving changelog release data to the UI."""

from __future__ import annotations

import logging
import re
import time
from collections import OrderedDict
from copy import deepcopy
from datetime import date
from hashlib import sha256
from json import dumps
from pathlib import Path
from threading import RLock
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from flask import Flask, jsonify, request


logger = logging.getLogger(__name__)

DEFAULT_FULL_CHANGELOG_URL = (
    "https://github.com/CyanAutomation/motioninocean/blob/main/docs/CHANGELOG.md"
)
DEFAULT_REMOTE_CHANGELOG_URL = (
    "https://raw.githubusercontent.com/CyanAutomation/motioninocean/main/docs/CHANGELOG.md"
)
_RELEASE_HEADING_PATTERN = re.compile(
    r"^##\s+\[(?P<version>[^\]]+)\](?:\s+-\s+(?P<date>\d{4}-\d{2}-\d{2}))?\s*$"
)
_BULLET_PATTERN = re.compile(r"^\s*-\s+(?P<entry>.+?)\s*$")
DEFAULT_REMOTE_CACHE_TTL_SECONDS = 300.0
DEFAULT_REMOTE_FAILURE_BACKOFF_SECONDS = 10.0
_CHANGELOG_CACHE_MAX_ENTRIES = 32
_CHANGELOG_CACHE: OrderedDict[tuple[Any, ...], tuple[float | None, dict[str, Any]]] = OrderedDict()
_CHANGELOG_CACHE_LOCK = RLock()


def _cache_get(key: tuple[Any, ...], now: float) -> dict[str, Any] | None:
    """Return an unexpired copy of a cached changelog payload."""
    with _CHANGELOG_CACHE_LOCK:
        cached = _CHANGELOG_CACHE.get(key)
        if cached is None:
            return None
        expires_at, payload = cached
        if expires_at is not None and now >= expires_at:
            del _CHANGELOG_CACHE[key]
            return None
        _CHANGELOG_CACHE.move_to_end(key)
        return deepcopy(payload)


def _cache_put(
    key: tuple[Any, ...], payload: dict[str, Any], expires_at: float | None = None
) -> None:
    """Store a changelog payload and evict the least recently used entries."""
    with _CHANGELOG_CACHE_LOCK:
        _CHANGELOG_CACHE[key] = (expires_at, deepcopy(payload))
        _CHANGELOG_CACHE.move_to_end(key)
        while len(_CHANGELOG_CACHE) > _CHANGELOG_CACHE_MAX_ENTRIES:
            _CHANGELOG_CACHE.popitem(last=False)


def _clear_changelog_cache() -> None:
    """Clear process-level changelog state for isolated application tests."""
    with _CHANGELOG_CACHE_LOCK:
        _CHANGELOG_CACHE.clear()


def parse_changelog_markdown(
    markdown_text: str, include_unreleased: bool = False
) -> list[dict[str, Any]]:
    """Parse Keep-a-Changelog markdown into normalized release entries.

    Args:
        markdown_text: Full markdown content from docs/CHANGELOG.md.
        include_unreleased: Whether to keep the ``Unreleased`` heading in output.

    Returns:
        List of release entries in file order.
    """
    entries: list[dict[str, Any]] = []
    current_entry: dict[str, Any] | None = None

    for raw_line in markdown_text.splitlines():
        heading_match = _RELEASE_HEADING_PATTERN.match(raw_line)
        if heading_match:
            if current_entry is not None:
                entries.append(current_entry)

            version = heading_match.group("version").strip()
            if version.lower() == "unreleased" and not include_unreleased:
                current_entry = None
                continue

            release_date_str = heading_match.group("date")
            parsed_date = _parse_iso_date(release_date_str)
            current_entry = {
                "version": version,
                "release_date": release_date_str,
                "release_date_iso": parsed_date.isoformat() if parsed_date else None,
                "changes": [],
            }
            continue

        bullet_match = _BULLET_PATTERN.match(raw_line)
        if bullet_match and current_entry is not None:
            current_entry["changes"].append(bullet_match.group("entry"))

    if current_entry is not None:
        entries.append(current_entry)

    return entries


def _fetch_remote_changelog_markdown(remote_url: str, timeout_seconds: float) -> str:
    """Fetch changelog markdown from a remote URL.

    Args:
        remote_url: Absolute URL to remote changelog markdown.
        timeout_seconds: Request timeout in seconds.

    Returns:
        Remote markdown text.

    Raises:
        OSError: When remote fetch fails.
    """
    try:
        with urlopen(remote_url, timeout=timeout_seconds) as response:  # nosec B310
            result = response.read().decode("utf-8")
            return cast("str", result)
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError) as exc:
        message = f"Remote changelog fetch failed for {remote_url}"
        raise OSError(message) from exc


def load_changelog_entries(  # noqa: PLR0913
    changelog_path: Path,
    include_unreleased: bool = False,
    remote_url: str = DEFAULT_REMOTE_CHANGELOG_URL,
    remote_timeout_seconds: float = 3.0,
    full_changelog_url: str = DEFAULT_FULL_CHANGELOG_URL,
    remote_cache_ttl_seconds: float = DEFAULT_REMOTE_CACHE_TTL_SECONDS,
    remote_failure_backoff_seconds: float = DEFAULT_REMOTE_FAILURE_BACKOFF_SECONDS,
) -> dict[str, Any]:
    """Load and parse changelog entries from local or remote markdown.

    Args:
        changelog_path: Absolute path to changelog markdown file.
        include_unreleased: Whether to include ``Unreleased`` heading entries.
        remote_url: Remote markdown URL fallback when local read fails.
        remote_timeout_seconds: Timeout for remote changelog request.
        full_changelog_url: Stable URL for full changelog UI links.
        remote_cache_ttl_seconds: Lifetime of successful remote results.
        remote_failure_backoff_seconds: Lifetime of failed remote results.

    Returns:
        Response-ready dict with status metadata and parsed entries.
    """
    resolved_path = changelog_path.resolve()
    common_key = (str(resolved_path), include_unreleased, full_changelog_url)

    with _CHANGELOG_CACHE_LOCK:
        try:
            file_stat = resolved_path.stat()
            local_key = (
                "local",
                *common_key,
                file_stat.st_mtime_ns,
                file_stat.st_size,
            )
            cached_payload = _cache_get(local_key, time.monotonic())
            if cached_payload is not None:
                return cached_payload
            markdown_text = resolved_path.read_text(encoding="utf-8")
        except OSError:
            markdown_text = None

        if markdown_text is not None:
            entries = parse_changelog_markdown(markdown_text, include_unreleased=include_unreleased)
            payload = {
                "status": "ok",
                "entries": entries,
                "message": f"Loaded {len(entries)} changelog release entries.",
                "source_type": "local",
                "full_changelog_url": full_changelog_url,
            }
            _cache_put(local_key, payload)
            return deepcopy(payload)

        if not changelog_path.exists():
            logger.warning(
                "changelog_local_missing",
                extra={
                    "changelog_path": str(changelog_path),
                    "fallback_source_type": "remote",
                    "remote_url": remote_url,
                },
            )
        else:
            logger.exception(
                "changelog_local_read_failed",
                extra={
                    "changelog_path": str(changelog_path),
                    "fallback_source_type": "remote",
                    "remote_url": remote_url,
                },
            )

        remote_key = (
            "remote",
            *common_key,
            remote_url,
            remote_timeout_seconds,
            remote_cache_ttl_seconds,
            remote_failure_backoff_seconds,
        )
        now = time.monotonic()
        cached_payload = _cache_get(remote_key, now)
        if cached_payload is not None:
            return cached_payload

        try:
            markdown_text = _fetch_remote_changelog_markdown(remote_url, remote_timeout_seconds)
        except OSError:
            logger.exception(
                "changelog_remote_fetch_failed",
                extra={
                    "changelog_path": str(changelog_path),
                    "remote_url": remote_url,
                    "remote_timeout_seconds": remote_timeout_seconds,
                    "source_type": "remote",
                },
            )
            message = "Changelog unavailable from local file and remote source."
            payload = {
                "status": "degraded",
                "entries": [],
                "message": message,
                "source_type": "remote",
                "full_changelog_url": full_changelog_url,
            }
            _cache_put(
                remote_key,
                payload,
                expires_at=now + max(0.0, remote_failure_backoff_seconds),
            )
            return deepcopy(payload)

        entries = parse_changelog_markdown(markdown_text, include_unreleased=include_unreleased)
        logger.info(
            "changelog_remote_loaded",
            extra={
                "changelog_path": str(changelog_path),
                "remote_url": remote_url,
                "remote_timeout_seconds": remote_timeout_seconds,
                "entry_count": len(entries),
                "source_type": "remote",
            },
        )
        payload = {
            "status": "ok",
            "entries": entries,
            "message": f"Loaded {len(entries)} changelog release entries from remote source.",
            "source_type": "remote",
            "full_changelog_url": full_changelog_url,
        }
        _cache_put(remote_key, payload, expires_at=now + max(0.0, remote_cache_ttl_seconds))
        return deepcopy(payload)


def register_changelog_routes(app: Flask) -> None:
    """Register API route for changelog entries.

    Args:
        app: Flask app instance.
    """

    @app.route("/api/changelog", methods=["GET"])
    def api_changelog():
        """Return parsed changelog entries for the utility modal."""
        changelog_path = Path(
            app.config.get("CHANGELOG_PATH", Path(__file__).parent.parent / "docs" / "CHANGELOG.md")
        )
        motion_config = getattr(app, "motion_config", {})
        remote_url = app.config.get(
            "CHANGELOG_REMOTE_URL",
            motion_config.get("changelog_remote_url", DEFAULT_REMOTE_CHANGELOG_URL),
        )
        remote_timeout_seconds = app.config.get(
            "CHANGELOG_REMOTE_TIMEOUT_SECONDS",
            motion_config.get("changelog_remote_timeout_seconds", 3.0),
        )
        full_changelog_url = app.config.get("CHANGELOG_FULL_URL", DEFAULT_FULL_CHANGELOG_URL)
        remote_cache_ttl_seconds = app.config.get(
            "CHANGELOG_REMOTE_CACHE_TTL_SECONDS",
            motion_config.get(
                "changelog_remote_cache_ttl_seconds", DEFAULT_REMOTE_CACHE_TTL_SECONDS
            ),
        )
        remote_failure_backoff_seconds = app.config.get(
            "CHANGELOG_REMOTE_FAILURE_BACKOFF_SECONDS",
            motion_config.get(
                "changelog_remote_failure_backoff_seconds",
                DEFAULT_REMOTE_FAILURE_BACKOFF_SECONDS,
            ),
        )

        payload = load_changelog_entries(
            changelog_path,
            remote_url=remote_url,
            remote_timeout_seconds=remote_timeout_seconds,
            full_changelog_url=full_changelog_url,
            remote_cache_ttl_seconds=remote_cache_ttl_seconds,
            remote_failure_backoff_seconds=remote_failure_backoff_seconds,
        )
        status_code = 200 if payload["status"] == "ok" else 503

        if payload["status"] != "ok":
            logger.warning(
                "api_changelog_degraded",
                extra={
                    "reason": payload["message"],
                    "source_type": payload.get("source_type", "unknown"),
                    "full_changelog_url": payload.get("full_changelog_url"),
                },
            )

        payload["source"] = str(changelog_path)
        response = jsonify(payload)
        response.status_code = status_code
        validator = sha256(
            dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        response.set_etag(validator)
        if status_code == 200:
            response.make_conditional(request)
        return response


def _parse_iso_date(raw_date: str | None) -> date | None:
    """Parse an ISO date string.

    Args:
        raw_date: Date string in ``YYYY-MM-DD`` format.

    Returns:
        Parsed ``date`` object when valid, otherwise ``None``.
    """
    if not raw_date:
        return None

    try:
        return date.fromisoformat(raw_date)
    except ValueError:
        return None
