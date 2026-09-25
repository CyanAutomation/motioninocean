---
name: release-publish
description: Verify the Docker image and GitHub Release created by the tag-triggered publish workflow. Use after pushing a valid vMAJOR.MINOR.PATCH tag or when diagnosing publication failures.
owner: motion-in-ocean team
last-reviewed: 2026-09-25
category: CI/CD
compatible-repo-areas:
  - .github/workflows/docker-publish.yml
  - docs/CHANGELOG.md
  - VERSION
---

## Purpose

Confirm that release verification, image publication, and GitHub Release creation completed with the expected version and notes.

## Scope and trigger conditions

- Use after a version tag has been pushed or when the release workflow fails.
- Use [`release-operator`](../release-operator/SKILL.md) to prepare and push the tag.
- This skill verifies outputs; it does not create or push tags.

## Required inputs

- Release tag such as `v1.2.3` and its Actions run.
- GitHub access to view workflow logs and release metadata.
- Docker access when validating an image pull locally.

## Step-by-step workflow

1. Read the run for `.github/workflows/docker-publish.yml` and confirm the tag passed the `vMAJOR.MINOR.PATCH` check.
2. Confirm the `verify` job passed `make ci`, `make security`, image build, and fixed HIGH/CRITICAL Trivy enforcement.
3. Confirm the `build` job published the `linux/amd64` and `linux/arm64` image manifest.
4. Confirm the `release` job extracted the matching section from `docs/CHANGELOG.md` and created a GitHub Release.
5. Verify the GHCR image tags: `vX.Y.Z`, `X.Y.Z`, `X.Y`, and `latest`. The workflow also publishes matching tags to Docker Hub.
6. Pull the exact version tag when local verification is needed:

   ```bash
   docker pull ghcr.io/cyanautomation/motioninocean:X.Y.Z
   ```

7. If a job fails, preserve the tag and inspect the failed step. Retry a transient run only after confirming that no source or policy fix is needed.

## Validation checklist

- [ ] Correct version tag triggered the workflow.
- [ ] Verify and image-security jobs passed.
- [ ] Multi-architecture manifest contains amd64 and arm64.
- [ ] GHCR and Docker Hub tags are present.
- [ ] GitHub Release notes match the version section in `docs/CHANGELOG.md`.
- [ ] Exact-version image pull succeeds when checked locally.

## Source of truth

- `.github/workflows/docker-publish.yml` — Tag trigger, CI/security checks, image tags, architectures, and release creation.
- `docs/CHANGELOG.md` — Release note source.
- `VERSION` — Expected project version.
- `docs/guides/RELEASE.md` — Operator procedure and failure recovery.

## Common failure modes and recovery actions

- **Failure:** Workflow cannot find release notes. **Recovery:** Confirm the tagged commit contains a matching `## [X.Y.Z]` section in `docs/CHANGELOG.md`, then follow the maintainer-approved correction process.
- **Failure:** Image build or push fails. **Recovery:** Inspect registry authentication, build logs, and architecture manifest checks.
- **Failure:** Trivy blocks the image. **Recovery:** Review the report, update affected packages/base image, and publish a corrected version.
- **Failure:** GH Release is missing after image publication. **Recovery:** Inspect the `release` job permissions and log; do not rewrite the version tag.
- **Failure:** One architecture is absent. **Recovery:** Treat the release as incomplete and investigate the Buildx manifest verification step.

## Related Skills

- [`release-operator`](../release-operator/SKILL.md) — Prepare the release.
- [`ci-triage`](../ci-triage/SKILL.md) — Diagnose failing workflow jobs.
- [`ci-quality-gates`](../ci-quality-gates/SKILL.md) — Run the local validation suite.

## Maintenance notes

Update this skill when image names/tags, architectures, changelog extraction, workflow permissions, or security policy change.
