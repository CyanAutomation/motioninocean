"""Integration tests for /api/changelog endpoint."""

from pathlib import Path

from flask import Flask

from pi_camera_in_docker import changelog_api
from pi_camera_in_docker.changelog_api import register_changelog_routes


def _build_test_app(changelog_path: str) -> Flask:
    app = Flask(__name__)
    app.config["CHANGELOG_PATH"] = changelog_path
    app.config["CHANGELOG_FULL_URL"] = changelog_api.DEFAULT_FULL_CHANGELOG_URL
    app.config["CHANGELOG_REMOTE_URL"] = changelog_api.DEFAULT_REMOTE_CHANGELOG_URL
    app.config["CHANGELOG_REMOTE_TIMEOUT_SECONDS"] = 0.1
    register_changelog_routes(app)
    return app


def test_api_changelog_returns_newest_first_from_file_order(tmp_path: Path) -> None:
    """Endpoint returns release entries in file order, newest first."""
    changelog_path = tmp_path / "CHANGELOG.md"
    changelog_path.write_text(
        """# Changelog
## [Unreleased]
- Future change

## [2.0.0] - 2026-02-26
- Newest item

## [1.0.0] - 2025-01-01
- Older item
""",
        encoding="utf-8",
    )

    app = _build_test_app(str(changelog_path))
    client = app.test_client()
    response = client.get("/api/changelog")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["source_type"] == "local"
    assert payload["full_changelog_url"] == changelog_api.DEFAULT_FULL_CHANGELOG_URL
    assert [entry["version"] for entry in payload["entries"]] == ["2.0.0", "1.0.0"]
    assert payload["entries"][0]["changes"] == ["Newest item"]


def test_api_changelog_missing_file_returns_degraded_with_source_metadata() -> None:
    """Endpoint degrades gracefully and includes source metadata for UI diagnostics."""
    app = _build_test_app("/tmp/definitely-missing-changelog-file.md")
    client = app.test_client()
    response = client.get("/api/changelog")

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["status"] == "degraded"
    assert payload["entries"] == []
    assert payload["source_type"] == "remote"
    assert payload["source"] == "/tmp/definitely-missing-changelog-file.md"
    assert payload["full_changelog_url"] == changelog_api.DEFAULT_FULL_CHANGELOG_URL


def test_api_changelog_missing_file_falls_back_to_remote(monkeypatch) -> None:
    """Endpoint should return remote changelog when local file is unavailable."""
    app = _build_test_app("/tmp/definitely-missing-changelog-file.md")
    client = app.test_client()

    monkeypatch.setattr(
        changelog_api,
        "_fetch_remote_changelog_markdown",
        lambda remote_url, timeout_seconds: "## [3.0.0] - 2026-03-01\n- Remote fallback\n",
    )

    response = client.get("/api/changelog")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["source_type"] == "remote"
    assert payload["entries"][0]["version"] == "3.0.0"


def test_api_changelog_remote_fallback_includes_source_metadata(monkeypatch) -> None:
    """Remote fallback response preserves source metadata expected by UI."""
    app = _build_test_app("/tmp/another-missing-changelog-file.md")
    client = app.test_client()

    monkeypatch.setattr(
        changelog_api,
        "_fetch_remote_changelog_markdown",
        lambda remote_url, timeout_seconds: "## [3.1.0] - 2026-03-02\n- Remote source metadata\n",
    )

    response = client.get("/api/changelog")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["source_type"] == "remote"
    assert payload["source"] == "/tmp/another-missing-changelog-file.md"
    assert payload["full_changelog_url"] == changelog_api.DEFAULT_FULL_CHANGELOG_URL
