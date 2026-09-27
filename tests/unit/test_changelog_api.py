"""Unit tests for changelog markdown parsing."""

from pathlib import Path

import pytest

from pi_camera_in_docker import changelog_api
from pi_camera_in_docker.changelog_api import load_changelog_entries, parse_changelog_markdown


@pytest.fixture(autouse=True)
def clear_changelog_cache() -> None:
    """Keep process cache entries isolated between unit tests."""
    changelog_api._clear_changelog_cache()


def test_parse_changelog_markdown_returns_released_versions_only_by_default() -> None:
    """Parser returns only released versions, excluding [Unreleased] section by default.

    Contract: When include_unreleased=False (default), parse_changelog_markdown()
    must exclude any [Unreleased] section and return only version entries with
    semantic version numbers in [X.Y.Z] format, preserving file order.
    """
    markdown = """# Changelog
## [Unreleased]
- Future item that should not appear

## [1.2.0] - 2026-02-26
- Added feature A
- Fixed issue B

## [1.1.0] - 2026-02-20
- Older change
"""

    entries = parse_changelog_markdown(markdown)

    # Must contain exactly 2 entries (both released versions, no Unreleased)
    assert len(entries) == 2, f"Expected 2 entries, got {len(entries)}"

    # Verify correct versions in correct order
    versions = [entry["version"] for entry in entries]
    assert versions == ["1.2.0", "1.1.0"], f"Expected [1.2.0, 1.1.0], got {versions}"

    # Verify first entry has correct metadata
    assert entries[0]["release_date"] == "2026-02-26", (
        "First entry should be v1.2.0 with date 2026-02-26"
    )
    assert entries[0]["changes"] == ["Added feature A", "Fixed issue B"], (
        "First entry changes should match exactly"
    )

    # Verify second entry exists and is not Unreleased
    assert entries[1]["version"] == "1.1.0"
    assert "Unreleased" not in str(entries), "Unreleased should not appear in any returned entry"


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


def test_load_changelog_entries_reads_local_file_and_sets_metadata(tmp_path: Path) -> None:
    """Local changelog reads return source metadata and full URL."""
    changelog_path = tmp_path / "CHANGELOG.md"
    changelog_path.write_text("## [1.0.0] - 2026-01-01\n- Initial release\n", encoding="utf-8")

    payload = load_changelog_entries(changelog_path)

    assert payload["status"] == "ok"
    assert payload["source_type"] == "local"
    assert payload["entries"][0]["version"] == "1.0.0"
    assert payload["full_changelog_url"] == changelog_api.DEFAULT_FULL_CHANGELOG_URL


def test_load_changelog_entries_missing_file_uses_remote_fallback(
    monkeypatch, tmp_path: Path
) -> None:
    """Missing local changelog should fallback to remote markdown parsing."""
    monkeypatch.setattr(
        changelog_api,
        "_fetch_remote_changelog_markdown",
        lambda remote_url, timeout_seconds: "## [2.0.0] - 2026-02-01\n- Remote release\n",
    )

    payload = load_changelog_entries(tmp_path / "missing.md")

    assert payload["status"] == "ok"
    assert payload["source_type"] == "remote"
    assert "remote source" in payload["message"]
    assert payload["entries"][0]["version"] == "2.0.0"
    assert payload["full_changelog_url"] == changelog_api.DEFAULT_FULL_CHANGELOG_URL


def test_load_changelog_entries_remote_failure_returns_degraded_with_link(
    monkeypatch, tmp_path: Path
) -> None:
    """When local and remote fail, degraded payload still includes full URL."""

    def _raise_remote_error(remote_url: str, timeout_seconds: float) -> str:
        raise OSError("network down")

    monkeypatch.setattr(changelog_api, "_fetch_remote_changelog_markdown", _raise_remote_error)

    payload = load_changelog_entries(tmp_path / "missing.md")

    assert payload["status"] == "degraded"
    assert payload["entries"] == []
    assert payload["source_type"] == "remote"
    assert payload["full_changelog_url"] == changelog_api.DEFAULT_FULL_CHANGELOG_URL


def test_load_changelog_entries_includes_ui_expected_source_metadata(tmp_path: Path) -> None:
    """Payload includes source metadata consumed by API/UI contracts."""
    changelog_path = tmp_path / "CHANGELOG.md"
    changelog_path.write_text("## [1.0.0] - 2026-01-01\n- Initial release\n", encoding="utf-8")

    payload = load_changelog_entries(changelog_path)

    assert payload["status"] == "ok"
    assert payload["source_type"] == "local"
    assert "source" not in payload
    assert payload["full_changelog_url"] == changelog_api.DEFAULT_FULL_CHANGELOG_URL


def test_local_changelog_cache_hits_and_invalidates_on_file_change(
    monkeypatch, tmp_path: Path
) -> None:
    """Local results are reused until path metadata changes."""
    changelog_path = tmp_path / "CHANGELOG.md"
    changelog_path.write_text("## [1.0.0]\n- One\n", encoding="utf-8")
    parse_calls = 0
    real_parser = changelog_api.parse_changelog_markdown

    def counting_parser(markdown_text: str, include_unreleased: bool = False):
        nonlocal parse_calls
        parse_calls += 1
        return real_parser(markdown_text, include_unreleased)

    monkeypatch.setattr(changelog_api, "parse_changelog_markdown", counting_parser)

    assert load_changelog_entries(changelog_path)["entries"][0]["version"] == "1.0.0"
    assert load_changelog_entries(changelog_path)["entries"][0]["version"] == "1.0.0"
    assert parse_calls == 1

    changelog_path.write_text("## [2.0.0]\n- Two, changed\n", encoding="utf-8")
    assert load_changelog_entries(changelog_path)["entries"][0]["version"] == "2.0.0"
    assert parse_calls == 2


def test_remote_cache_expires_using_monotonic_time(monkeypatch, tmp_path: Path) -> None:
    """A successful remote result is fetched again after its configured TTL."""
    clock = [100.0]
    fetches = 0

    def fetch_remote(remote_url: str, timeout_seconds: float) -> str:
        nonlocal fetches
        fetches += 1
        return f"## [{fetches}.0.0]\n- Remote\n"

    monkeypatch.setattr(changelog_api.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(changelog_api, "_fetch_remote_changelog_markdown", fetch_remote)
    path = tmp_path / "missing.md"

    first = load_changelog_entries(path, remote_cache_ttl_seconds=5)
    clock[0] += 4
    cached = load_changelog_entries(path, remote_cache_ttl_seconds=5)
    clock[0] += 2
    expired = load_changelog_entries(path, remote_cache_ttl_seconds=5)

    assert first["entries"] == cached["entries"]
    assert expired["entries"][0]["version"] == "2.0.0"
    assert fetches == 2


def test_remote_failure_uses_retry_backoff(monkeypatch, tmp_path: Path) -> None:
    """Remote failures are negatively cached for the configured backoff."""
    clock = [10.0]
    fetches = 0

    def fail_remote(remote_url: str, timeout_seconds: float) -> str:
        nonlocal fetches
        fetches += 1
        raise OSError("offline")

    monkeypatch.setattr(changelog_api.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(changelog_api, "_fetch_remote_changelog_markdown", fail_remote)
    path = tmp_path / "missing.md"

    load_changelog_entries(path, remote_failure_backoff_seconds=3)
    load_changelog_entries(path, remote_failure_backoff_seconds=3)
    assert fetches == 1
    clock[0] += 3
    load_changelog_entries(path, remote_failure_backoff_seconds=3)
    assert fetches == 2


def test_remote_cache_isolated_by_path_and_url(monkeypatch, tmp_path: Path) -> None:
    """Different application paths and remote URLs do not share results."""
    fetches: list[str] = []

    def fetch_remote(remote_url: str, timeout_seconds: float) -> str:
        fetches.append(remote_url)
        return f"## [{len(fetches)}.0.0]\n- Remote\n"

    monkeypatch.setattr(changelog_api, "_fetch_remote_changelog_markdown", fetch_remote)
    first_path = tmp_path / "first.md"
    second_path = tmp_path / "second.md"

    load_changelog_entries(first_path, remote_url="https://example.test/one")
    load_changelog_entries(first_path, remote_url="https://example.test/two")
    load_changelog_entries(second_path, remote_url="https://example.test/one")
    load_changelog_entries(first_path, remote_url="https://example.test/one")

    assert fetches == [
        "https://example.test/one",
        "https://example.test/two",
        "https://example.test/one",
    ]
