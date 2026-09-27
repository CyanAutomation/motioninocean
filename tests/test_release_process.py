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


def test_manifest_verification_uses_lowercase_repository_and_build_digest() -> None:
    """Manifest verification targets the exact build digest at a lowercase GHCR path."""
    workflow = (REPO_ROOT / ".github/workflows/docker-publish.yml").read_text(encoding="utf-8")
    section = workflow.split("- name: Verify published multi-architecture manifest", 1)[1]
    section = section.split("\n  release:", 1)[0]

    lowercase_assignment = 'REPO_LOWER="${GITHUB_REPOSITORY,,}"'
    inspect_command = 'docker buildx imagetools inspect --raw "ghcr.io/${REPO_LOWER}@$IMAGE_DIGEST"'
    assert lowercase_assignment in section
    assert "IMAGE_DIGEST: ${{ steps.build_bookworm.outputs.digest }}" in section
    assert inspect_command in section
    assert section.index(lowercase_assignment) < section.index(inspect_command)
    assert "linux/amd64" in section
    assert "linux/arm64" in section


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


def test_release_guide_documents_image_attestation_verification() -> None:
    guide = (REPO_ROOT / "docs/guides/RELEASE.md").read_text(encoding="utf-8")
    assert "oci://ghcr.io/cyanautomation/motioninocean:" in guide
    assert "oci://index.docker.io/cyanautomation/motioninocean:" in guide
    assert (
        "--signer-workflow CyanAutomation/motioninocean/.github/workflows/docker-publish.yml"
        in guide
    )
