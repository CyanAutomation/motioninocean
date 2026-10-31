"""Keep manual GitHub releases and Docker publishing behavior aligned."""

import re
import shlex
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def _release_workflow() -> dict[str, Any]:
    workflow_path = REPO_ROOT / ".github/workflows/docker-publish.yml"
    return yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_release_publishing_is_manual_but_docker_workflow_still_runs() -> None:
    """A published GitHub Release triggers image publishing without creating a release."""
    workflow = _release_workflow()
    workflow_text = (REPO_ROOT / ".github/workflows/docker-publish.yml").read_text(encoding="utf-8")

    assert workflow["on"]["release"]["types"] == ["published"]
    assert "release" not in workflow["jobs"]
    assert "gh release create" not in workflow_text
    assert "gh release edit" not in workflow_text

    for job_name in ("verify", "build", "publish"):
        assert "github.event_name == 'release'" in workflow["jobs"][job_name]["if"]


def test_release_workflow_accepts_two_component_v_tags() -> None:
    """The release pipeline accepts vX.Y tags and validates the release event tag."""
    workflow = _release_workflow()
    validation = next(
        step
        for step in workflow["jobs"]["verify"]["steps"]
        if step.get("name") == "Validate release tag"
    )

    assert validation["if"] == "github.event_name == 'release'"
    assert validation["env"]["RELEASE_TAG"] == "${{ github.event.release.tag_name }}"
    assert r"^v[0-9]+\.[0-9]+$" in validation["run"]


def test_release_operator_docs_describe_the_manual_release_and_image_contract() -> None:
    """Guidance agrees that operators create releases and automation publishes images."""
    guide = (REPO_ROOT / "docs/guides/RELEASE.md").read_text(encoding="utf-8")
    operator = (REPO_ROOT / ".github/skills/release-operator/SKILL.md").read_text(encoding="utf-8")
    publisher = (REPO_ROOT / ".github/skills/release-publish/SKILL.md").read_text(encoding="utf-8")

    assert "https://github.com/CyanAutomation/motioninocean/releases/new" in guide
    assert "`vX.Y`" in guide
    assert "does not create or edit GitHub Releases" in guide
    assert "docker pull ghcr.io/cyanautomation/motioninocean:vX.Y" in guide
    assert "GitHub Releases UI" in operator
    assert "`vX.Y`" in operator
    assert "manual" in operator.lower()
    assert "`vX.Y`" in publisher
    assert "`latest`" in publisher
    assert "created manually" in publisher

    for obsolete_reference in (
        "create-release.sh",
        "vX.Y.Z",
        "vMAJOR.MINOR.PATCH",
        "X.Y.Z",
        "release job",
        "release creation",
    ):
        assert obsolete_reference not in operator
        assert obsolete_reference not in publisher


def test_manifest_verification_uses_candidate_digest_and_both_architectures() -> None:
    """Candidate manifest verification targets the exact lowercase GHCR digest."""
    workflow = _release_workflow()
    build = workflow["jobs"]["build"]
    verify_manifest = next(
        step
        for step in build["steps"]
        if step.get("name") == "Verify candidate multi-architecture manifest"
    )

    assert verify_manifest["env"]["IMAGE_REF"] == "${{ steps.candidate-ref.outputs.image_ref }}"
    assert 'docker buildx imagetools inspect --raw "$IMAGE_REF"' in verify_manifest["run"]
    assert "linux/amd64" in verify_manifest["run"]
    assert "linux/arm64" in verify_manifest["run"]


def test_release_guide_verification_commands_match_attested_images() -> None:
    """Guide commands verify both images with the publisher workflow identity."""
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

    workflow = _release_workflow()
    publish_steps = workflow["jobs"]["publish"]["steps"]
    attested_images = {
        step["with"]["subject-name"]
        for step in publish_steps
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
        assert image_reference.endswith(":vX.Y")
        documented_images.add(image_reference.removeprefix("oci://").removesuffix(":vX.Y"))

    assert documented_images == attested_images
