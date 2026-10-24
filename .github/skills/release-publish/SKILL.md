---
name: release-publish
description: Verify container images after a motion-in-ocean GitHub Release is published. Use after the release workflow completes or when image publishing fails.
owner: motion-in-ocean team
last-reviewed: 2026-10-24
category: CI/CD
compatible-repo-areas:
  - .github/workflows/docker-publish.yml
  - docs/guides/RELEASE.md
  - docs/CHANGELOG.md
  - VERSION
---

## Purpose

Confirm the container images published after a manual GitHub Release use the expected version, platforms, and provenance.

## Scope and trigger conditions

- Use after publishing a GitHub Release through the UI, or when its container image workflow fails.
- Use [`release-operator`](../release-operator/SKILL.md) to prepare and publish the GitHub Release.
- This skill checks the resulting container images; the GitHub Release itself is created manually.

## Required inputs

- A published release tag such as `v1.2` and its Actions run.
- GitHub access to inspect workflow logs and release metadata.
- Docker access when pulling or inspecting an image locally.

## Step-by-step workflow

1. Confirm the GitHub Release uses a two-component `vX.Y` tag and its notes match the release section in `docs/CHANGELOG.md`.
2. In `.github/workflows/docker-publish.yml`, confirm the `verify` job passed `make ci` and `make security`.
3. Confirm the `build` job created the multi-architecture candidate and recorded its immutable digest.
4. Confirm the `scan` job passed for both amd64 and arm64, and `arm64-smoke` imported the application from the candidate digest.
5. Confirm the `publish` job completed its `container-release` approval when required, promoted the candidate to GHCR and Docker Hub, verified both manifests, and attached provenance.
6. Confirm both registries contain the `vX.Y` and `latest` tags for `linux/amd64` and `linux/arm64`.
7. Pull the versioned GHCR image when local verification is needed:

   ```bash
   docker pull ghcr.io/cyanautomation/motioninocean:vX.Y
   ```

8. When provenance verification is needed, follow the `gh attestation verify` commands in [`docs/guides/RELEASE.md`](../../../docs/guides/RELEASE.md) for both registries.
9. If a workflow job fails, inspect its logs and correct the cause. Do not rewrite or reuse the published release tag.

## Validation checklist

- [ ] The published GitHub Release uses the intended `vX.Y` tag and changelog notes.
- [ ] `verify`, both platform scans, and the ARM64 smoke test passed.
- [ ] The `container-release` approval completed if required.
- [ ] GHCR and Docker Hub have `vX.Y` and `latest` manifests for amd64 and arm64.
- [ ] Published platform digests match the verified candidate.
- [ ] Provenance is attached to both registry images and verifies when checked.
- [ ] Pulling the exact version tag succeeds when checked locally.

## Source of truth

- `.github/workflows/docker-publish.yml` — Release event, verification jobs, image tags, platforms, and provenance.
- `docs/guides/RELEASE.md` — Manual GitHub Release procedure and provenance commands.
- `docs/CHANGELOG.md` — Release note source.
- `VERSION` — Expected project version.

## Common failure modes and recovery actions

- **Failure:** The release event does not start the image workflow. **Recovery:** Confirm the GitHub Release was published and inspect the Actions run list.
- **Failure:** Verification, scan, or ARM64 smoke test fails. **Recovery:** Diagnose the failed job and correct the source or image policy before retrying.
- **Failure:** Publishing waits for approval. **Recovery:** Review and approve the `container-release` deployment if authorized by the release process.
- **Failure:** One registry tag or architecture is missing. **Recovery:** Treat publication as incomplete and inspect the promotion and manifest verification steps.
- **Failure:** Provenance verification fails. **Recovery:** Check the attestation subject, registry authentication, and signer workflow shown in the release guide.

## Related Skills

- [`release-operator`](../release-operator/SKILL.md) — Prepare and publish the GitHub Release.
- [`ci-triage`](../ci-triage/SKILL.md) — Diagnose failing workflow jobs.
- [`ci-quality-gates`](../ci-quality-gates/SKILL.md) — Run the local validation suite.

## Maintenance notes

Update this skill when image names or tags, architectures, workflow permissions, provenance, or release verification steps change.
