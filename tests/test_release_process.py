"""Protect release tooling from stale paths and automatic history rewrites."""

import re
import shlex
import subprocess
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_release_tools_use_repository_changelog() -> None:
    """The release script and workflow both use the canonical changelog."""
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/docker-publish.yml").read_text(encoding="utf-8")
    )
    changelog_step = next(
        step
        for step in workflow["jobs"]["release"]["steps"]
        if step.get("name") == "Extract changelog for release"
    )
    assert (
        'scripts/extract_release_changelog.sh "$VERSION" docs/CHANGELOG.md' in changelog_step["run"]
    )

    release_script = (REPO_ROOT / "create-release.sh").read_text(encoding="utf-8")
    assert 'CHANGELOG_FILE="docs/CHANGELOG.md"' in release_script


def _extract_changelog(version: str, changelog_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            str(REPO_ROOT / "scripts" / "extract_release_changelog.sh"),
            version,
            str(changelog_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_release_changelog_extractor_returns_only_requested_version(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "## [1.2.30] - 2026-10-11\n\n- Similar version\n\n"
        "## [Unreleased]\n\n- Work in progress\n\n"
        "## [1.2.3] - 2026-10-10\n\n- Added camera support\n- Fixed stream startup\n\n"
        "## [1.2.2] - 2026-09-01\n\n- Older change\n",
        encoding="utf-8",
    )

    result = _extract_changelog("1.2.3", changelog)

    assert result.returncode == 0, result.stderr
    assert result.stdout == "- Added camera support\n- Fixed stream startup\n"


def test_release_changelog_extractor_uses_fallback_when_section_is_missing(
    tmp_path: Path,
) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("## [1.2.2] - 2026-09-01\n\n- Older change\n", encoding="utf-8")

    result = _extract_changelog("1.2.3", changelog)

    assert result.returncode == 0, result.stderr
    assert result.stdout == "Release 1.2.3 - See commit history for details.\n"


def test_release_changelog_extractor_uses_fallback_when_file_is_missing(tmp_path: Path) -> None:
    result = _extract_changelog("1.2.3", tmp_path / "missing.md")

    assert result.returncode == 0, result.stderr
    assert result.stdout == "Release 1.2.3 - See commit history for details.\n"


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


def test_release_guide_verification_commands_match_attested_images() -> None:
    """Guide commands verify both images with the publisher's workflow identity."""
    guide = (REPO_ROOT / "docs/guides/RELEASE.md").read_text(encoding="utf-8")
    code_blocks = re.findall(r"```bash\n(.*?)```", guide, flags=re.DOTALL)
    attestation_block = next(block for block in code_blocks if "gh attestation verify" in block)
    tokens = shlex.split(re.sub(r"\\\n\s*", " ", attestation_block))
    command_starts = [
        index
        for index in range(len(tokens))
        if tokens[index : index + 3] == ["gh", "attestation", "verify"]
    ]
    commands = [
        tokens[start : command_starts[index + 1] if index + 1 < len(command_starts) else None]
        for index, start in enumerate(command_starts)
    ]

    workflow = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/docker-publish.yml").read_text(encoding="utf-8")
    )
    build_steps = workflow["jobs"]["build"]["steps"]
    attested_images = {
        step["with"]["subject-name"]
        for step in build_steps
        if step.get("name", "").startswith("Attest ")
    }

    assert len(commands) == 2
    documented_images = set()
    for command in commands:
        assert command[:3] == ["gh", "attestation", "verify"]
        assert command[4:6] == ["--repo", "CyanAutomation/motioninocean"]
        assert command[6:8] == [
            "--signer-workflow",
            "CyanAutomation/motioninocean/.github/workflows/docker-publish.yml",
        ]
        assert command[8:] == ["--bundle-from-oci"]
        image_reference = command[3]
        assert image_reference.endswith(":X.Y.Z")
        documented_images.add(image_reference.removeprefix("oci://").removesuffix(":X.Y.Z"))

    assert documented_images == attested_images
