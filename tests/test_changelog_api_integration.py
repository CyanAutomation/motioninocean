"""Integration tests for /api/changelog endpoint."""

from pathlib import Path

from flask import Flask

from pi_camera_in_docker.changelog_api import register_changelog_routes


def _build_test_app(changelog_path: str) -> Flask:
    app = Flask(__name__)
    app.config["CHANGELOG_PATH"] = changelog_path
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
    assert [entry["version"] for entry in payload["entries"]] == ["2.0.0", "1.0.0"]
    assert payload["entries"][0]["changes"] == ["Newest item"]


def test_api_changelog_missing_file_returns_degraded() -> None:
    """Endpoint degrades gracefully when changelog file is absent."""
    app = _build_test_app("/tmp/definitely-missing-changelog-file.md")
    client = app.test_client()
    response = client.get("/api/changelog")

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["status"] == "degraded"
    assert payload["entries"] == []
