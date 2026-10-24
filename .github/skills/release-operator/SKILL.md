---
name: release-operator
description: Prepare a manual motion-in-ocean GitHub release and confirm its container images are published. Use when updating the version or release notes, or publishing a release.
owner: motion-in-ocean team
last-reviewed: 2026-10-24
category: CI/CD
compatible-repo-areas:
  - docs/guides/RELEASE.md
  - docs/CHANGELOG.md
  - VERSION
  - pyproject.toml
  - .github/workflows/docker-publish.yml
---

## Purpose

Prepare and publish a GitHub Release through the UI, then confirm the corresponding container images are available.

## Scope and trigger conditions

- Use when preparing or publishing a versioned release from `main`.
- Use [`release-publish`](../release-publish/SKILL.md) to check the container images after publishing.
- Do not use for ordinary fixes or to rewrite an existing release tag.

## Required inputs

- The intended `X.Y` version and finalized `## [X.Y]` notes in `docs/CHANGELOG.md`.
- `VERSION` and the Python project version in `pyproject.toml` updated to `X.Y`.
- The version and changelog updates merged to `main`, with required CI checks passing.
- GitHub access to create a release and inspect its Actions run.

## Step-by-step workflow

1. Review [`docs/guides/RELEASE.md`](../../../docs/guides/RELEASE.md) and confirm the version, changelog section, and version files agree.
2. Confirm the release commit is on `main`, the worktree is clean, and required checks pass.
3. Open the [GitHub Releases UI](https://github.com/CyanAutomation/motioninocean/releases/new). Create a release with tag and title `vX.Y`, target `main`, and notes from the matching changelog section.
4. Publish the GitHub Release. This triggers the container image verification and publishing workflow; approve the `container-release` environment if GitHub requests approval.
5. Follow [`release-publish`](../release-publish/SKILL.md) to check the workflow and published images.
6. If image publishing fails, inspect the failed Actions step and correct the cause. Do not rewrite or reuse the published release tag.

## Validation checklist

- [ ] `VERSION`, `pyproject.toml`, and the changelog section use the same `X.Y` version.
- [ ] The GitHub Release uses tag and title `vX.Y` and targets `main`.
- [ ] Release notes match the `## [X.Y]` changelog section.
- [ ] Container image verification and publishing completed successfully.
- [ ] GHCR and Docker Hub have the `vX.Y` and `latest` images.

## Source of truth

- `docs/guides/RELEASE.md` — Manual release procedure, version format, and recovery steps.
- `docs/CHANGELOG.md` — User-facing release notes.
- `VERSION` and `pyproject.toml` — Project version values.
- `.github/workflows/docker-publish.yml` — Verification and container image publishing after a release is published.

## Common failure modes and recovery actions

- **Failure:** The version files and changelog disagree. **Recovery:** Correct them in a reviewed change before publishing the release.
- **Failure:** The tag format or release target is wrong. **Recovery:** Stop before publishing and correct the draft to use `vX.Y` targeting `main`.
- **Failure:** The workflow waits for approval. **Recovery:** Review and approve the `container-release` deployment if authorized by the repository’s release process.
- **Failure:** Image verification or publishing fails. **Recovery:** Inspect the failed job and use [`release-publish`](../release-publish/SKILL.md) to diagnose the artifact state.
- **Failure:** The GitHub Release has already been published with the wrong tag. **Recovery:** Do not rewrite or reuse the tag; follow the maintainer-approved correction process.

## Related Skills

- [`release-publish`](../release-publish/SKILL.md) — Verify the container images after publishing.
- [`ci-quality-gates`](../ci-quality-gates/SKILL.md) — Run local validation before release.
- [`ci-triage`](../ci-triage/SKILL.md) — Diagnose a failed Actions job.

## Maintenance notes

Review this skill when the release guide, version format, changelog process, or image publishing workflow changes.
