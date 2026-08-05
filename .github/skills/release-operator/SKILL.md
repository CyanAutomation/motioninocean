---
name: release-operator
description: Operate motion-in-ocean's tag-driven release automation, including preflight checks, release execution, workflow verification, and rollback handling. Use when creating, validating, or troubleshooting releases.
owner: motion-in-ocean team
last-reviewed: 2026-08-05
category: CI/CD
compatible-repo-areas:
  - create-release.sh
  - RELEASE.md
  - VERSION
  - CHANGELOG.md
  - .github/workflows/docker-publish.yml
---

## Purpose

Enable release operators to safely execute motion-in-ocean's semantic versioning release process. This skill covers preflight validation, tag creation, changelog management, workflow monitoring, and rollback procedures. Proper release execution ensures version tags trigger Docker image builds, GitHub releases are created with correct notes, and operators have recovery paths if workflows fail.

## Scope and trigger conditions

- Apply when preparing a new semantic version release.
- Apply when using `create-release.sh` to update `VERSION`, `CHANGELOG.md`, and git tags.
- Apply when diagnosing failed tag workflows, missing GHCR images, or GitHub Release issues.

## Required inputs

- Intended semantic version bump (patch/minor/major).
- Clean git working tree and push permissions.
- Access to GitHub Actions status (preferably via `gh` CLI).
- Confirmed changelog entries for the target version.

## Step-by-step workflow

1. Review `RELEASE.md` for the expected tag-driven lifecycle and rollback behavior.
2. Verify release prerequisites:
   - clean branch (`git status`)
   - release notes/changelog readiness (`CHANGELOG.md`)
   - GitHub access and optional `gh auth` status
3. Execute `./create-release.sh` and provide target semantic version.
4. Confirm script side effects:
   - `VERSION` updated
   - `CHANGELOG.md` updated
   - release commit created (`Release vX.Y.Z`)
   - git tag `vX.Y.Z` created and pushed
5. Monitor GitHub Actions release workflow defined in `.github/workflows/docker-publish.yml`.
6. Verify outputs:
   - GHCR images published for expected tags (`vX.Y.Z`, `X.Y.Z`, `X.Y`, optional `latest`)
   - GitHub Release created with changelog-derived notes
7. If workflow fails, follow rollback sequence from `RELEASE.md` (automatic or manual fallback).

## Validation checklist

- [ ] Versioning follows SemVer and matches intended change scope.
- [ ] Changelog section exists and is meaningful for target version.
- [ ] Docker publish workflow completed successfully for the tag.
- [ ] GitHub Release exists and references correct notes/images.
- [ ] Rollback path is confirmed when release automation fails.

## Related Skills

- **Pre-release validation:** [`ci-quality-gates`](../ci-quality-gates/SKILL.md) — Run full quality gates before release
- **Post-release verification:** [`release-publish`](../release-publish/SKILL.md) — Verify Docker/GitHub Release publication
- **If workflow fails:** [`ci-triage`](../ci-triage/SKILL.md) — Diagnose workflow step failures
- **Dependency updates before release:** [`dependabot-dependency-management`](../dependabot-dependency-management/SKILL.md) — Merge pending dependency PRs

## Source of truth

- `create-release.sh` — Script that performs version bumping and tag creation
- `RELEASE.md` — Detailed release process documentation and rollback procedures
- `VERSION` — Current semantic version (MAJOR.MINOR.PATCH)
- `CHANGELOG.md` — Release notes and version history (must include section for new version)
- `.github/workflows/docker-publish.yml` — Tag-triggered Docker build and GitHub release workflow

## Maintenance notes

- Review this skill quarterly and immediately when `create-release.sh`, `RELEASE.md`, or `.github/workflows/docker-publish.yml` changes
- Update `last-reviewed` field whenever release process changes
- Ensure pre-release checklist reflects current deployment and tagging requirements

## Common failure modes and recovery actions

- **Failure:** Workflow does not start on tag push.
  - **Recovery:** Verify tag pattern and `docker-publish.yml` trigger configuration.
- **Failure:** Workflow starts but image push fails.
  - **Recovery:** Inspect GHCR auth/permission logs and rerun after fixing token or package settings.
- **Failure:** Changelog extraction produces empty release notes.
  - **Recovery:** Add properly formatted `## [X.Y.Z]` section in `CHANGELOG.md` and recreate release.
- **Failure:** Verification tooling unavailable (`gh` missing/auth missing).
  - **Recovery:** Perform manual checks in GitHub Actions, GHCR package page, and release page; document reduced assurance.
