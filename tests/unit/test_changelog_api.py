"""Unit tests for changelog markdown parsing."""

from pathlib import Path

from pi_camera_in_docker.changelog_api import load_changelog_entries, parse_changelog_markdown


def test_parse_changelog_markdown_skips_unreleased_by_default() -> None:
    """Parser skips unreleased section and keeps release order from file."""
    markdown = """# Changelog
## [Unreleased]
- Future item

## [1.2.0] - 2026-02-26
- Added feature A
- Fixed issue B

## [1.1.0] - 2026-02-20
- Older change
"""

    entries = parse_changelog_markdown(markdown)

    assert [entry["version"] for entry in entries] == ["1.2.0", "1.1.0"]
    assert entries[0]["release_date"] == "2026-02-26"
    assert entries[0]["changes"] == ["Added feature A", "Fixed issue B"]


def test_parse_changelog_markdown_can_include_unreleased() -> None:
    """Parser includes unreleased section when explicitly requested."""
    markdown = """## [Unreleased]
- Planned work
## [1.0.0] - 2026-01-01
- Initial release
"""

    entries = parse_changelog_markdown(markdown, include_unreleased=True)

    assert entries[0]["version"] == "Unreleased"
    assert entries[0]["changes"] == ["Planned work"]


def test_load_changelog_entries_missing_file_returns_degraded(tmp_path: Path) -> None:
    """Missing changelog file returns degraded payload with empty entries."""
    payload = load_changelog_entries(tmp_path / "missing.md")

    assert payload["status"] == "degraded"
    assert payload["entries"] == []
    assert "not found" in payload["message"]
