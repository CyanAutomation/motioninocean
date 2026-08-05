---
name: release-publish
description: Run and verify the tag-triggered Docker/GitHub Release publication flow implemented by .github/workflows/docker-publish.yml.
owner: motion-in-ocean team
last-reviewed: 2026-08-05
category: CI/CD
compatible-repo-areas:
  - .github/workflows/docker-publish.yml
  - CHANGELOG.md
  - VERSION
  - RELEASE.md
---

## Purpose

Verify and troubleshoot the tag-triggered Docker image publication and GitHub Release creation flow. This skill helps operators understand what happens after a release tag is pushed, diagnose workflow failures, and validate that artifacts (GHCR images, GitHub Release) are correctly generated.

## Scope and trigger conditions

Apply this skill when:

- Verifying that Docker images were successfully published to GHCR for a release tag
- Checking that GitHub Release was created with correct release notes and artifact links
- Diagnosing `.github/workflows/docker-publish.yml` failures (build, publish, or release steps)
- Validating release artifacts before announcing to users
- Troubleshooting missing or malformed Docker tags, release notes, or GitHub Release

Do NOT use this skill for:

- Creating or pushing release tags (use [`release-operator`](../release-operator/SKILL.md) instead)
- Writing or updating workflow definition (that's a code change, not a release operation)
- Building Docker images locally (use `make docker-build`)

## Required inputs

- Access to GitHub Actions workflow runs (for `.github/workflows/docker-publish.yml`)
- Ability to query GHCR (GitHub Container Registry) for image tags
- Access to GitHub Releases page for validation
- Familiarity with release tag naming convention (`v*.*.*`)
- Optional: `gh` CLI for programmatic verification

## Step-by-step workflow

### Operational sequence (exact flow)

1. **Prepare version bump sources**
   - Update `VERSION` to the new semantic version (`X.Y.Z`).
   - Add a matching changelog section in `CHANGELOG.md` using header format: `## [X.Y.Z] - YYYY-MM-DD`.
   - Ensure related release documentation reflects the same version context (at minimum `RELEASE.md`; if used, align `create-release.sh` workflow notes).
2. **Create and push release tag**
   - Tag naming convention is **`v*.*.*`** (for example: `v1.12.3`).
   - Push the tag so the workflow trigger (`push.tags: 'v*.*.*'`) starts.
3. **Workflow build/publish path**
   - `Extract metadata` generates Docker tags.
   - `Build and push` publishes multi-arch images to GHCR (`linux/arm64`, `linux/amd64`).
4. **Release note generation path**
   - `Extract changelog for release` parses `CHANGELOG.md` section for the tag version (`vX.Y.Z` -> `X.Y.Z`).
   - `Build release notes` writes `/tmp/release_notes.md` with changelog content + Docker pull instructions + GHCR package URL.
   - `Validate release notes` blocks release creation if file is missing, empty, or too short.
5. **Publish GitHub release**
   - `Create GitHub Release` runs `gh release create` with:
     - title: `Release vX.Y.Z`
     - notes source: `/tmp/release_notes.md`

## Release preconditions

- Tag **must** follow `v*.*.*` or workflow will not auto-run.
- A changelog section for the exact version **must exist**: `## [X.Y.Z]` in `CHANGELOG.md`.
  - If missing, workflow falls back to generic text (`Release X.Y.Z - See commit history for details.`), which is considered a release quality failure for this project.
- Repository permissions must allow:
  - package push (`packages: write`)
  - release creation (`contents: write`)

## Expected artifacts

After a successful run for tag `vX.Y.Z`:

- **GHCR image tags** (from metadata action)
  - `ghcr.io/<owner>/<repo>:vX.Y.Z`
  - `ghcr.io/<owner>/<repo>:X.Y.Z`
  - `ghcr.io/<owner>/<repo>:X.Y`
  - `ghcr.io/<owner>/<repo>:latest` (default branch builds)
- **GitHub Release**
  - Release exists at `/releases/tag/vX.Y.Z`
  - Title: `Release vX.Y.Z`
  - Notes include:
    - changelog section body for `X.Y.Z`
    - Docker pull examples for `:vX.Y.Z`, `:X.Y.Z`, and `:latest`
    - link to GitHub Packages container page

## Related Skills

- **Before this step:** [`release-operator`](../release-operator/SKILL.md) — Creates the release tag
- **If workflow fails:** [`ci-triage`](../ci-triage/SKILL.md) — Diagnose workflow failures
- **Pre-release validation:** [`ci-quality-gates`](../ci-quality-gates/SKILL.md) — Ensure code quality before publishing

## Validation checklist

- [ ] GitHub Actions workflow run for tag `vX.Y.Z` completed successfully (all steps green)
- [ ] Docker image successfully published to GHCR with correct tags:
  - [ ] `ghcr.io/<owner>/<repo>:vX.Y.Z`
  - [ ] `ghcr.io/<owner>/<repo>:X.Y.Z`
  - [ ] `ghcr.io/<owner>/<repo>:X.Y`
  - [ ] `ghcr.io/<owner>/<repo>:latest` (if applicable)
- [ ] GitHub Release created at `/releases/tag/vX.Y.Z` and is published (not draft)
- [ ] Release title is `Release vX.Y.Z`
- [ ] Release notes include changelog details (not generic fallback text)
- [ ] Release notes include Docker pull commands and GHCR package link
- [ ] Test `docker pull ghcr.io/<owner>/<repo>:X.Y.Z` succeeds locally
- [ ] Release is linked in project announcements/changelog as appropriate

## Source of truth

- `.github/workflows/docker-publish.yml` — Exact workflow definition (trigger, steps, permissions)
- `CHANGELOG.md` — Changelog section must exist for release version before tag
- `VERSION` — Single source of truth for current release version
- `RELEASE.md` — Release planning and context (if applicable)
- GitHub Actions runs page — Live workflow execution logs and status
- GitHub Container Registry (GHCR) — Published images, tags, metadata
- GitHub Releases page — Published releases, release notes, artifacts

## Common failure modes and recovery actions

### Extract changelog for release

**Symptoms**

- Log shows: `Warning: No changelog section found for version X.Y.Z`
- Release notes begin with generic fallback text

**Root Cause**

- `CHANGELOG.md` missing exact header `## [X.Y.Z]` (requires version without `v` prefix)
- Tag/version mapping incorrect (`v1.2.3` must map to `1.2.3` in changelog header)

**Recovery**

- Confirm `CHANGELOG.md` includes exact header `## [X.Y.Z]` (no `v` prefix)
- Confirm tag/version mapping is correct (`v1.2.3` => `1.2.3`)
- If changelog is wrong, fix and create a new tag (old release is "downgraded" or deleted)

### Build release notes

**Symptoms**

- Step fails while reading `/tmp/changelog.txt`
- Release notes are missing Docker image instructions

**Root Cause**

- Prior step did not create `/tmp/changelog.txt`
- Repository variable resolution failed (`github.repository` invalid in workflow context)
- Script block has syntax errors or variable expansion issues

**Recovery**

- Verify prior "Extract changelog for release" step completed and logged output
- Check workflow permissions and context variables (`github.repository` should resolve correctly)
- Re-run workflow after fixing script block syntax
- Check GitHub Actions logs for explicit error messages

### Validate release notes

**Symptoms**

- Errors: `Release notes file not found`, `file is empty`, or `too short`
- Validation step blocks release creation

**Root Cause**

- `/tmp/release_notes.md` was not created by previous step
- Generated file is empty or below minimum length threshold
- Workflow permissions issue

**Recovery**

- Confirm `/tmp/release_notes.md` exists and is non-empty after prior steps
- Check file content in workflow logs preview output
- Ensure minimum content requirement is met (typically changelog + docker pull commands)
- Re-run workflow after verifying prior steps

### Create GitHub Release

**Symptoms**

- `gh release create` fails
- Release does not appear in GitHub UI after workflow completes
- Error: "Release already exists for tag X"

**Root Cause**

- `GH_TOKEN` missing or invalid (`secrets.GITHUB_TOKEN` not provided)
- Job permissions missing `contents: write`
- Release already exists for the tag (duplicate tag creation attempt)
- Tag does not exist remotely

**Recovery**

- Verify `secrets.GITHUB_TOKEN` is set and has `contents: write` permission
- Confirm tag exists remotely: `git tag -l | grep <tag>`
- If release already exists, edit existing release or delete and re-create
- Check workflow run logs for explicit `gh release create` error output
- Manually verify release exists: `gh release view <tag>` or GitHub web UI

### Docker image not available in GHCR

**Symptoms**

- Workflow completes but images not visible in GHCR
- `docker pull ghcr.io/<owner>/<repo>:X.Y.Z` fails: "image not found"

**Root Cause**

- "Build and push" step failed silently or was skipped
- Registry authentication (`GHCR_TOKEN` or `secrets.GITHUB_TOKEN`) missing or invalid
- Image build failed (Dockerfile errors, platform-specific issues)

**Recovery**

- Check "Build and push" step logs in GitHub Actions
- Verify `secrets.GITHUB_TOKEN` has `packages: write` permission
- Check if step was skipped due to branch/tag conditions
- If build failed: fix Dockerfile and create a new release tag
- Manually test build locally: `make docker-build-prod`

## Maintenance notes

- Review this skill quarterly; especially when `.github/workflows/docker-publish.yml` changes
- Update when GHCR tagging strategy, Docker image naming, or release notes format changes
- Document any new release preconditions or post-release validation steps
- Test workflow on actual releases; ensure all artifacts appear as expected

---

## Post-release verification checklist (Quick Reference)

- [ ] GitHub Actions run for tag `vX.Y.Z` completed successfully.
- [ ] GitHub Packages shows container package with tags:
  - [ ] `vX.Y.Z`
  - [ ] `X.Y.Z`
  - [ ] `X.Y`
  - [ ] `latest` (if applicable)
- [ ] GitHub Release `vX.Y.Z` exists and is published.
- [ ] Release notes include changelog details (not fallback generic text).
- [ ] Release notes include Docker pull commands and package link.
- [ ] Pull test succeeds for at least `ghcr.io/<owner>/<repo>:X.Y.Z`.
