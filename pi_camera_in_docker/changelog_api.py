"""Utilities for serving changelog release data to the UI."""

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

from flask import Flask, jsonify


logger = logging.getLogger(__name__)

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


def load_changelog_entries(
    changelog_path: Path,
    include_unreleased: bool = False,
) -> dict[str, Any]:
    """Load and parse changelog entries from disk.

    Args:
        changelog_path: Absolute path to changelog markdown file.
        include_unreleased: Whether to include ``Unreleased`` heading entries.

    Returns:
        Response-ready dict with status metadata and parsed entries.
    """
    if not changelog_path.exists():
        message = f"Changelog file not found: {changelog_path}"
        return {"status": "degraded", "entries": [], "message": message}

    try:
        markdown_text = changelog_path.read_text(encoding="utf-8")
    except OSError as exc:
        message = f"Changelog file is unreadable: {exc!s}"
        return {"status": "degraded", "entries": [], "message": message}

    entries = parse_changelog_markdown(markdown_text, include_unreleased=include_unreleased)
    return {
        "status": "ok",
        "entries": entries,
        "message": f"Loaded {len(entries)} changelog release entries.",
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

        payload = load_changelog_entries(changelog_path)
        status_code = 200 if payload["status"] == "ok" else 503

        if payload["status"] != "ok":
            logger.warning("api_changelog_degraded", extra={"reason": payload["message"]})

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
