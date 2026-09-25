# Release process

This guide describes the release procedure and its GitHub Actions automation. User-facing release notes are maintained in [`docs/CHANGELOG.md`](../CHANGELOG.md).

## Prerequisites

- Update and check out `main`.
- Use a clean working tree.
- Confirm the `## [Unreleased]` section in `docs/CHANGELOG.md` is ready to publish.
- Have push access to the repository.
- Install and authenticate the GitHub CLI if you want `create-release.sh` to monitor publication.

## Create a release

1. Run the project checks and review the changes on `main`.
2. Run `./create-release.sh` from the repository root.
3. Enter the next `MAJOR.MINOR.PATCH` version and review the summary.
4. Confirm the operation. The script updates `VERSION` and `docs/CHANGELOG.md`, creates a release commit and annotated `vX.Y.Z` tag, and pushes `main` and the tag.
5. The `Build and publish Docker image` workflow verifies the tag, runs CI and Bandit, scans the image, pushes multi-architecture images, and creates the GitHub Release.
6. Confirm the workflow succeeded, review release notes, and pull the published GHCR image.

The workflow creates the mutable `latest` container image tag. The release script does not create or force-update a Git tag named `latest`.

## Recovery after a failure

The release script does not automatically delete tags, reset commits, or force-push a branch. A failed or timed-out workflow leaves the release commit and tag available for diagnosis.

- If pushing `main` fails, inspect the remote changes and the local release commit before deciding how to proceed.
- If pushing the version tag fails after `main` was pushed, confirm that the local tag points to the intended release commit, then push that tag after fixing the cause:

  ```bash
  git show --no-patch --decorate vX.Y.Z
  git push origin vX.Y.Z
  ```

- If the workflow fails, inspect its logs and either rerun the failed workflow after fixing a transient issue or prepare a new patch release with a corrective change.
- If the GitHub CLI is missing or unauthenticated, check the Actions page and release page manually.

Treat published version tags as immutable. Coordinate any exceptional release withdrawal with maintainers rather than rewriting branch or tag history.

## Verification

```bash
# Recent workflow runs
gh run list --limit 5

# Inspect a workflow run
gh run view <run-id>

# Pull the published image
docker pull ghcr.io/cyanautomation/motioninocean:X.Y.Z

# View the release
gh release view vX.Y.Z
```

## Sources

- [`create-release.sh`](../../create-release.sh) — Version/changelog update, commit, tag, and verification.
- [`.github/workflows/docker-publish.yml`](../../.github/workflows/docker-publish.yml) — Release verification and publishing.
- [`docs/CHANGELOG.md`](../CHANGELOG.md) — Release notes.
