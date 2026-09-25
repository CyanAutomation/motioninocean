"""Protect release tooling from stale paths and automatic history rewrites."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_release_workflow_reads_repository_changelog() -> None:
    workflow = (REPO_ROOT / ".github/workflows/docker-publish.yml").read_text(encoding="utf-8")
    assert 'if [ -f "docs/CHANGELOG.md" ]' in workflow
    extraction = next(
        line for line in workflow.splitlines() if line.strip().startswith("CHANGELOG_CONTENT=$(awk")
    )
    assert "docs/CHANGELOG.md" in extraction


def test_release_failure_path_does_not_rewrite_or_delete_git_history() -> None:
    script = (REPO_ROOT / "create-release.sh").read_text(encoding="utf-8")
    forbidden_commands = (
        "git reset --hard",
        "git push -f",
        "git push --force",
        "git push origin --delete",
        "git tag -f",
    )
    for command in forbidden_commands:
        assert command not in script, f"Release script contains unsafe mutation: {command}"


def test_release_script_targets_documented_changelog() -> None:
    script = (REPO_ROOT / "create-release.sh").read_text(encoding="utf-8")
    assert 'CHANGELOG_FILE="docs/CHANGELOG.md"' in script
