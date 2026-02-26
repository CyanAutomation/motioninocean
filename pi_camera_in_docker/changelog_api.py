"""Utilities for serving changelog release data to the UI."""

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from flask import Flask, jsonify


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
            return response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError) as exc:
        message = f"Remote changelog fetch failed for {remote_url}"
        raise OSError(message) from exc


def load_changelog_entries(
    changelog_path: Path,
    include_unreleased: bool = False,
    remote_url: str = DEFAULT_REMOTE_CHANGELOG_URL,
    remote_timeout_seconds: float = 3.0,
    full_changelog_url: str = DEFAULT_FULL_CHANGELOG_URL,
) -> dict[str, Any]:
    """Load and parse changelog entries from local or remote markdown.

    Args:
        changelog_path: Absolute path to changelog markdown file.
        include_unreleased: Whether to include ``Unreleased`` heading entries.
        remote_url: Remote markdown URL fallback when local read fails.
        remote_timeout_seconds: Timeout for remote changelog request.
        full_changelog_url: Stable URL for full changelog UI links.

    Returns:
        Response-ready dict with status metadata and parsed entries.
    """
    try:
        markdown_text = changelog_path.read_text(encoding="utf-8")
    except OSError:
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
            return {
                "status": "degraded",
                "entries": [],
                "message": message,
                "source_type": "remote",
                "full_changelog_url": full_changelog_url,
            }

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
        return {
            "status": "ok",
            "entries": entries,
            "message": f"Loaded {len(entries)} changelog release entries from remote source.",
            "source_type": "remote",
            "full_changelog_url": full_changelog_url,
        }

    entries = parse_changelog_markdown(markdown_text, include_unreleased=include_unreleased)
    return {
        "status": "ok",
        "entries": entries,
        "message": f"Loaded {len(entries)} changelog release entries.",
        "source_type": "local",
        "full_changelog_url": full_changelog_url,
    }


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

        payload = load_changelog_entries(
            changelog_path,
            remote_url=remote_url,
            remote_timeout_seconds=remote_timeout_seconds,
            full_changelog_url=full_changelog_url,
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
        return jsonify(payload), status_code


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
