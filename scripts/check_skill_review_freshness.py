#!/usr/bin/env python3
"""Report skill documents whose source review date is over 100 days old."""

from __future__ import annotations

import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPOSITORY_ROOT / ".github" / "skills"
MAX_REVIEW_AGE_DAYS = 100
LAST_REVIEWED_LINE = re.compile(r"^last-reviewed:\s*(\S+)\s*$", re.MULTILINE)


def find_review_issues(
    skill_files: list[Path], *, today: date, max_age_days: int = MAX_REVIEW_AGE_DAYS
) -> list[str]:
    """Return invalid or stale review-date diagnostics for skill documents."""
    issues: list[str] = []
    for path in skill_files:
        content = path.read_text(encoding="utf-8")
        if not content.startswith("---\n"):
            issues.append(f"{path}: missing frontmatter with a valid ISO date for last-reviewed")
            continue

        frontmatter_parts = content.split("---\n", 2)
        if len(frontmatter_parts) != 3:
            issues.append(f"{path}: malformed frontmatter; missing closing --- delimiter")
            continue

        frontmatter = frontmatter_parts[1]
        match = LAST_REVIEWED_LINE.search(frontmatter)
        try:
            reviewed = date.fromisoformat(match.group(1)) if match else None
        except ValueError:
            reviewed = None
        if reviewed is None:
            issues.append(f"{path}: missing valid ISO date for last-reviewed")
            continue

        age_days = (today - reviewed).days
        if age_days < 0:
            issues.append(f"{path}: review date {reviewed.isoformat()} is in the future")
        elif age_days > max_age_days:
            issues.append(
                f"{path}: review is {age_days} days old; refresh it within {max_age_days} days"
            )
    return issues


def main() -> int:
    """Check all non-template skill documents against the 100-day review policy."""
    skill_files = [
        path for path in sorted(SKILLS_ROOT.glob("*/SKILL.md")) if path.parent.name != "_template"
    ]
    today = datetime.now(timezone.utc).date()
    issues = find_review_issues(skill_files, today=today)
    if issues:
        sys.stderr.write("Skill review freshness check failed:\n")
        for issue in issues:
            sys.stderr.write(f"- {issue}\n")
        return 1

    sys.stdout.write(f"All {len(skill_files)} skill documents were reviewed within 100 days.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
