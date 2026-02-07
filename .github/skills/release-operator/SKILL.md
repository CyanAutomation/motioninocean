---
name: release-operator
description: Operate motion-in-ocean's tag-driven release automation, including preflight checks, release execution, workflow verification, and rollback handling. Use when creating, validating, or troubleshooting releases.
---

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

## Common failure modes and recovery actions

- **Failure:** Workflow does not start on tag push.
  - **Recovery:** Verify tag pattern and `docker-publish.yml` trigger configuration.
- **Failure:** Workflow starts but image push fails.
  - **Recovery:** Inspect GHCR auth/permission logs and rerun after fixing token or package settings.
- **Failure:** Changelog extraction produces empty release notes.
  - **Recovery:** Add properly formatted `## [X.Y.Z]` section in `CHANGELOG.md` and recreate release.
- **Failure:** Verification tooling unavailable (`gh` missing/auth missing).
  - **Recovery:** Perform manual checks in GitHub Actions, GHCR package page, and release page; document reduced assurance.
