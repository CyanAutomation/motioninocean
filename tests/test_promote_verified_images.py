"""Behavioral regression tests for the multi-registry image promoter."""

import json
import os
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMOTION_SCRIPT = PROJECT_ROOT / "scripts" / "promote-verified-images.sh"
AMD64_DIGEST = f"sha256:{'a' * 64}"
ARM64_DIGEST = f"sha256:{'b' * 64}"
GHCR_INDEX_DIGEST = f"sha256:{'c' * 64}"
DOCKER_HUB_INDEX_DIGEST = f"sha256:{'d' * 64}"
IMAGE_REF = f"ghcr.io/cyanautomation/motioninocean@{GHCR_INDEX_DIGEST}"
GHCR_TAG = "ghcr.io/cyanautomation/motioninocean:latest"
GHCR_VERSION_TAG = "ghcr.io/cyanautomation/motioninocean:v1.1"
DOCKER_HUB_TAG = "cyanautomation/motioninocean:latest"
DOCKER_HUB_VERSION_TAG = "cyanautomation/motioninocean:v1.1"
PRODUCTION_TAGS = [GHCR_TAG, GHCR_VERSION_TAG, DOCKER_HUB_TAG, DOCKER_HUB_VERSION_TAG]

FAKE_DOCKER = """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
state_path = Path(os.environ["FAKE_DOCKER_STATE"])
state = json.loads(state_path.read_text()) if state_path.exists() else {}

if args[:4] == ["buildx", "imagetools", "inspect", "--raw"]:
    reference = args[4]
    state[reference] = state.get(reference, 0) + 1
    state_path.write_text(json.dumps(state))
    failures = int(os.environ.get("FAKE_INSPECT_FAILURES_PER_REF", "0"))
    if state[reference] <= failures:
        print(f"simulated temporary registry error for {reference}", file=sys.stderr)
        raise SystemExit(255)
    manifest_path = (
        os.environ["FAKE_CANDIDATE_MANIFEST"]
        if reference == os.environ["IMAGE_REF"]
        else os.environ["FAKE_PUBLISHED_MANIFEST"]
    )
    sys.stdout.write(Path(manifest_path).read_text())
    raise SystemExit(0)

if args[:3] == ["buildx", "imagetools", "create"]:
    tag = args[args.index("--tag") + 1]
    metadata_path = Path(args[args.index("--metadata-file") + 1])
    digest = (
        os.environ["FAKE_GHCR_INDEX_DIGEST"]
        if tag.startswith("ghcr.io/")
        else os.environ["FAKE_DOCKER_HUB_INDEX_DIGEST"]
    )
    metadata_path.write_text(
        json.dumps({"containerimage.descriptor": {"digest": digest}})
    )
    print(f"created {tag}")
    raise SystemExit(0)

print(f"unexpected fake docker arguments: {args}", file=sys.stderr)
raise SystemExit(64)
"""


def make_manifest(arm64_digest=ARM64_DIGEST):
    """Build an OCI index with the two supported platforms and an attestation descriptor."""
    return {
        "schemaVersion": 2,
        "manifests": [
            {
                "digest": AMD64_DIGEST,
                "platform": {"os": "linux", "architecture": "amd64"},
            },
            {
                "digest": arm64_digest,
                "platform": {"os": "linux", "architecture": "arm64"},
            },
            {
                "digest": f"sha256:{'e' * 64}",
                "platform": {"os": "unknown", "architecture": "unknown"},
            },
        ],
    }


def run_promoter(tmp_path, *, published_manifest=None, failures_per_ref=0, max_attempts=4):
    """Run the promotion script with a fake Docker CLI and local manifest fixtures."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(FAKE_DOCKER)
    fake_docker.chmod(0o755)

    candidate_path = tmp_path / "candidate.json"
    published_path = tmp_path / "published.json"
    candidate_path.write_text(json.dumps(make_manifest()))
    published_path.write_text(json.dumps(published_manifest or make_manifest()))
    output_path = tmp_path / "github-output.txt"
    output_path.write_text("")

    env = os.environ.copy()
    env.update(
        {
            "DOCKER_METADATA_TAGS": "\n".join(PRODUCTION_TAGS),
            "FAKE_CANDIDATE_MANIFEST": str(candidate_path),
            "FAKE_DOCKER_STATE": str(tmp_path / "inspect-counts.json"),
            "FAKE_DOCKER_HUB_INDEX_DIGEST": DOCKER_HUB_INDEX_DIGEST,
            "FAKE_GHCR_INDEX_DIGEST": GHCR_INDEX_DIGEST,
            "FAKE_INSPECT_FAILURES_PER_REF": str(failures_per_ref),
            "FAKE_PUBLISHED_MANIFEST": str(published_path),
            "GITHUB_OUTPUT": str(output_path),
            "IMAGE_REF": IMAGE_REF,
            "INSPECT_MAX_ATTEMPTS": str(max_attempts),
            "INSPECT_RETRY_BASE_DELAY_SECONDS": "0",
            "PATH": f"{fake_bin}{os.pathsep}{env['PATH']}",
            "RUNNER_TEMP": str(tmp_path),
        }
    )
    result = subprocess.run(
        ["bash", str(PROMOTION_SCRIPT)],
        check=False,
        capture_output=True,
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
    )
    return result, output_path, env["FAKE_DOCKER_STATE"]


def test_promoter_copies_metadata_digest_and_checks_platforms(tmp_path):
    result, output_path, _ = run_promoter(tmp_path)

    assert result.returncode == 0, result.stderr
    assert output_path.read_text().splitlines() == [
        f"ghcr_digest={GHCR_INDEX_DIGEST}",
        f"dockerhub_digest={DOCKER_HUB_INDEX_DIGEST}",
    ]
    assert result.stdout.count("created ") == len(PRODUCTION_TAGS)
    assert f"Inspecting {IMAGE_REF}" in result.stdout
    for tag in PRODUCTION_TAGS:
        assert f"Inspecting {tag}" in result.stdout


def test_promoter_retries_registry_inspection_with_reference_diagnostics(tmp_path):
    result, _, state_path = run_promoter(tmp_path, failures_per_ref=1)
    inspect_counts = json.loads(Path(state_path).read_text())

    assert result.returncode == 0, result.stderr
    assert inspect_counts[IMAGE_REF] == 2
    assert "attempt 1/4 failed" in result.stderr
    assert "simulated temporary registry error" in result.stderr


def test_promoter_reports_reference_after_exhausted_inspection_retries(tmp_path):
    result, _, state_path = run_promoter(
        tmp_path,
        failures_per_ref=9,
        max_attempts=2,
    )
    inspect_counts = json.loads(Path(state_path).read_text())

    assert result.returncode != 0
    assert inspect_counts[IMAGE_REF] == 2
    assert IMAGE_REF in result.stderr
    assert "after 2 attempts" in result.stderr
    assert "simulated temporary registry error" in result.stderr
    assert "created " not in result.stdout


def test_promoter_rejects_a_published_platform_digest_mismatch(tmp_path):
    result, _, _ = run_promoter(
        tmp_path,
        published_manifest=make_manifest(arm64_digest=f"sha256:{'f' * 64}"),
    )

    assert result.returncode != 0
    assert "Published platform digests do not match" in result.stderr
    assert GHCR_TAG in result.stderr
    assert result.stdout.count("created ") == len(PRODUCTION_TAGS)
