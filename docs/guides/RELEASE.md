# Release Process

## Scope of this document

This file describes **how to cut and publish releases** (procedure + automation only).

- User-visible release notes belong in [`CHANGELOG.md`](../../CHANGELOG.md).
- Test validation evidence belongs in [`docs/testing/README.md`](../testing/README.md).

## Overview

Releases are tag-driven and automated:

```text
create-release.sh -> git tag (vX.Y.Z) -> GitHub Actions -> GHCR image + GitHub Release
```

## Prerequisites

- Clean working tree.
- Push access to the repository.
- GitHub Actions enabled.
- `gh` CLI installed/authenticated if you want automated workflow verification.

## Standard release flow

1. Verify clean repository state.
2. Run `./create-release.sh`.
3. Provide the next semantic version when prompted.
4. Confirm the release.
5. Let the script:
   - update `VERSION`,
   - stage release metadata,
   - create/push `Release vX.Y.Z` commit,
   - create/push `vX.Y.Z` tag,
   - monitor GitHub Actions,
   - confirm GHCR publish.

## Automation behavior

The release automation is expected to:

- Trigger on tags matching `v*.*.*`.
- Build/publish the Docker image.
- Publish GitHub release notes from changelog content.
- Roll back release tag/commit if the publish workflow fails.

## Rollback

If automated rollback does not complete, perform manually:

```bash
git push origin --delete vX.Y.Z
git tag -d vX.Y.Z
git reset --hard HEAD~1
git push -f origin <default-branch>
```

Then remove the GitHub release if it was created:

```bash
gh release delete vX.Y.Z --yes
```

## Verification commands

```bash
# Recent workflow runs
gh run list --limit 5

# Inspect a run
gh run view <run-id>

# Confirm published image
docker pull ghcr.io/hyzhak/pi-camera-in-docker:X.Y.Z

# Confirm GitHub release
gh release view vX.Y.Z
```
