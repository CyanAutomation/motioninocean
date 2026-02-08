---
name: release-publish
description: Run and verify the tag-triggered Docker/GitHub Release publication flow implemented by .github/workflows/docker-publish.yml.
---

## Purpose

Use this skill when you are preparing, executing, or validating a production release that is published via `.github/workflows/docker-publish.yml`.

## Operational sequence (exact flow)

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

## Troubleshooting by workflow step

### Extract changelog for release

**Symptoms**

- Log shows: `Warning: No changelog section found for version X.Y.Z`
- Release notes begin with generic fallback text.

**Checks and fixes**

- Confirm `CHANGELOG.md` includes exact header `## [X.Y.Z]` (no `v` prefix in the bracketed version).
- Confirm tag/version mapping is correct (`v1.2.3` => `1.2.3`).
- Re-run release with corrected changelog (new tag) if notes quality is unacceptable.

### Build release notes

**Symptoms**

- Step fails while reading `/tmp/changelog.txt`.
- Notes are missing Docker image instructions.

**Checks and fixes**

- Ensure prior step completed and wrote `/tmp/changelog.txt`.
- Verify repository variable resolution (`github.repository`) is valid in workflow context.
- Re-run workflow after fixing script block syntax or variable expansion.

### Validate release notes

**Symptoms**

- Errors like `Release notes file not found`, `file is empty`, or `too short`.

**Checks and fixes**

- Confirm `/tmp/release_notes.md` is created by previous step.
- Confirm generated file is non-empty and above minimum length threshold.
- Inspect step logs preview output to verify expected content shape.

### Create GitHub Release

**Symptoms**

- `gh release create` fails or release not visible in GitHub UI.

**Checks and fixes**

- Verify `GH_TOKEN` is present (`secrets.GITHUB_TOKEN`) and job permissions include `contents: write`.
- Confirm tag still exists remotely.
- Check for duplicate existing release for same tag; edit/delete and rerun as needed.

## Post-release verification checklist

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
