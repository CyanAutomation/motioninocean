from datetime import date, timedelta

from scripts.check_skill_review_freshness import find_review_issues


def test_review_freshness_uses_an_explicit_date_and_reports_stale_or_invalid_files(tmp_path):
    today = date(2026, 11, 17)
    current = tmp_path / "current" / "SKILL.md"
    boundary = tmp_path / "boundary" / "SKILL.md"
    stale = tmp_path / "stale" / "SKILL.md"
    invalid = tmp_path / "invalid" / "SKILL.md"
    for path in (current, boundary, stale, invalid):
        path.parent.mkdir()

    current.write_text(f"---\nlast-reviewed: {today.isoformat()}\n---\n", encoding="utf-8")
    boundary.write_text(
        f"---\nlast-reviewed: {(today - timedelta(days=100)).isoformat()}\n---\n",
        encoding="utf-8",
    )
    stale.write_text(
        f"---\nlast-reviewed: {(today - timedelta(days=101)).isoformat()}\n---\n",
        encoding="utf-8",
    )
    invalid.write_text("---\nlast-reviewed: soon\n---\n", encoding="utf-8")

    issues = find_review_issues([current, boundary, stale, invalid], today=today)

    assert len(issues) == 2
    assert any("stale/SKILL.md" in issue and "101 days" in issue for issue in issues)
    assert any("invalid/SKILL.md" in issue and "valid ISO date" in issue for issue in issues)
