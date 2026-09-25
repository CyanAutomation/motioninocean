---
name: release-operator
description: Prepare a motion-in-ocean semantic-version release from main and verify its publication. Use when updating VERSION, release notes, or a version tag.
owner: motion-in-ocean team
last-reviewed: 2026-09-25
category: CI/CD
compatible-repo-areas:
  - create-release.sh
  - docs/guides/RELEASE.md
  - docs/CHANGELOG.md
  - VERSION
  - .github/workflows/docker-publish.yml
---

## Purpose

Prepare the release metadata, push an immutable version tag, and verify the publishing workflow.

## Scope and trigger conditions

- Use for a versioned release from the default `main` branch.
- Use [`release-publish`](../release-publish/SKILL.md) to validate workflow outputs.
- Do not use for ordinary fixes or undocumented manual pushes.

## Required inputs

- Approved release version and ready `## [Unreleased]` notes in `docs/CHANGELOG.md`.
- Updated `main` branch, clean worktree, and push access.
- GitHub CLI installed/authenticated for automatic workflow monitoring.

## Step-by-step workflow

1. Review [`docs/guides/RELEASE.md`](../../../docs/guides/RELEASE.md) and confirm the version and changelog content.
2. Check `git status` and confirm the intended release commit is based on `main`.
3. Run `./create-release.sh`, enter the semantic version, review its summary, and confirm only when the `VERSION`, changelog, commit, and tag operations are intended.
4. The script pushes the release commit to `main` and the annotated `vX.Y.Z` tag. It does not rewrite refs on failure; inspect and recover from the printed state.
5. Monitor `.github/workflows/docker-publish.yml` and verify the GitHub Release and container images.
6. If publication fails, keep the version commit/tag for diagnosis. Fix and rerun a transient workflow failure or publish a corrective patch release.

## Validation checklist

- [ ] Release is based on current `main` with a clean worktree.
- [ ] `VERSION` and `docs/CHANGELOG.md` contain the intended version.
- [ ] Tag `vX.Y.Z` points to the release commit.
- [ ] Release workflow passes verification and image security checks.
- [ ] GHCR images and GitHub Release exist with expected notes.

## Source of truth

- `create-release.sh` — Release preflight, metadata, commit/tag push, and workflow monitoring.
- `docs/guides/RELEASE.md` — Release and recovery procedure.
- `docs/CHANGELOG.md` — Version history and release notes.
- `VERSION` — Current semantic version.
- `.github/workflows/docker-publish.yml` — Tag validation, CI/security checks, image publishing, and GitHub Release.

## Common failure modes and recovery actions

- **Failure:** Script rejects the branch or worktree. **Recovery:** Update `main`, finish or stash unrelated changes, and rerun.
- **Failure:** Tag already exists. **Recovery:** Inspect the existing tag and release; do not overwrite a published version.
- **Failure:** The workflow fails or times out. **Recovery:** Inspect Actions logs; the commit and tag remain for diagnosis. Retry only after understanding the failure.
- **Failure:** GitHub CLI cannot verify the run. **Recovery:** Inspect the Actions and Releases pages manually.

## Related Skills

- [`ci-quality-gates`](../ci-quality-gates/SKILL.md) — Validate changes before release.
- [`release-publish`](../release-publish/SKILL.md) — Verify published artifacts.
- [`ci-triage`](../ci-triage/SKILL.md) — Diagnose workflow failures.

## Maintenance notes

Review this skill when `create-release.sh`, the release guide, versioning, or the publish workflow changes.
