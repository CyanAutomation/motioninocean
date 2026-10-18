"""Protect release tooling from stale paths and automatic history rewrites."""

import os
import re
import shlex
import shutil
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


def test_release_push_failure_preserves_local_commit_and_version_tags(tmp_path: Path) -> None:
    """A failed push leaves the release commit and existing tags available for recovery.

    Traceability: docs/guides/RELEASE.md#recovery-after-a-failure.
    """
    repository = tmp_path / "repository"
    repository.mkdir()
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"], cwd=repository, check=True
    )

    (repository / "docs").mkdir()
    (repository / "VERSION").write_text("1.2.2\n", encoding="utf-8")
    (repository / "docs" / "CHANGELOG.md").write_text(
        "## [Unreleased]\n\n- Pending change\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "VERSION", "docs/CHANGELOG.md"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-m", "Initial release state"], cwd=repository, check=True)
    subprocess.run(
        ["git", "tag", "-a", "v1.2.2", "-m", "Previous release"],
        cwd=repository,
        check=True,
    )
    subprocess.run(["git", "remote", "add", "origin", str(origin)], cwd=repository, check=True)
    original_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repository, check=True, capture_output=True, text=True
    ).stdout.strip()
    original_tag = subprocess.run(
        ["git", "rev-parse", "refs/tags/v1.2.2"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    real_git = shutil.which("git")
    assert real_git is not None
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    git_wrapper = fake_bin / "git"
    git_wrapper.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "push" ]; then echo "simulated push failure" >&2; exit 1; fi\n'
        f'exec {shlex.quote(real_git)} "$@"\n',
        encoding="utf-8",
    )
    git_wrapper.chmod(0o755)
    test_env = os.environ.copy()
    test_env["PATH"] = f"{fake_bin}{os.pathsep}{test_env['PATH']}"

    result = subprocess.run(
        ["bash", str(REPO_ROOT / "create-release.sh")],
        cwd=repository,
        env=test_env,
        input="1.2.3\ny\n",
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "simulated push failure" in result.stderr
    assert "local commit and tag are retained" in result.stderr
    release_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repository, check=True, capture_output=True, text=True
    ).stdout.strip()
    assert release_commit != original_commit
    assert (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", original_commit, release_commit],
            cwd=repository,
            check=False,
        ).returncode
        == 0
    )
    assert (
        subprocess.run(
            ["git", "rev-parse", "refs/tags/v1.2.2"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == original_tag
    )
    assert (
        subprocess.run(
            ["git", "rev-parse", "refs/tags/v1.2.3^{commit}"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == release_commit
    )
    assert (repository / "VERSION").read_text(encoding="utf-8") == "1.2.3\n"


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
