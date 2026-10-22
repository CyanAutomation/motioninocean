# Releases

Create GitHub Releases manually through the [GitHub Releases page](https://github.com/CyanAutomation/motioninocean/releases/new). The Docker publishing workflow runs after a release is published; it verifies the source, builds and scans the multi-architecture image, then publishes the image to GHCR and Docker Hub. It does not create or edit GitHub Releases.

## Version format

Use two numeric components in release tags and titles: `vX.Y` (for example, `v1.0`, `v1.1`, or `v2.0`). Keep the leading `v` in the Git tag and release title. Store the version without the `v` prefix in `VERSION` and `pyproject.toml`.

Before publishing a release, merge the version and changelog updates to `main`. Keep the `## [Unreleased]` section in `docs/CHANGELOG.md` current, and add a `## [X.Y] - YYYY-MM-DD` section for user-facing changes included in the release.

## Create a release in GitHub

1. Confirm the intended code and version updates are merged to `main` and the CI checks pass.
2. Open [Draft a new release](https://github.com/CyanAutomation/motioninocean/releases/new).
3. Choose a new tag named `vX.Y`, such as `v1.0`, and set the target to `main`.
4. Set the release title to the same `vX.Y` value.
5. Add the release notes from the matching `docs/CHANGELOG.md` section. GitHub's generated notes can also be used and edited in the form.
6. Publish the release. This triggers the Docker publishing workflow.
7. Review the workflow run and approve the `container-release` environment if GitHub requests its configured approval.

Use the next `X.Y` version for each release. Do not reuse an existing tag, rewrite a published tag, or delete tags when cleaning up GitHub Release entries.

## Verify the published images

The workflow publishes matching multi-architecture images for `linux/arm64` and `linux/amd64` with the tags `vX.Y` and `latest`:

```bash
docker pull ghcr.io/cyanautomation/motioninocean:vX.Y
docker pull cyanautomation/motioninocean:vX.Y
```

It also attaches signed provenance to each registry image. Authenticate to the registries before verification (`docker login ghcr.io` for GHCR; `docker login` for Docker Hub):

```bash
gh attestation verify \
  oci://ghcr.io/cyanautomation/motioninocean:vX.Y \
  --repo CyanAutomation/motioninocean \
  --signer-workflow CyanAutomation/motioninocean/.github/workflows/docker-publish.yml \
  --bundle-from-oci

gh attestation verify \
  oci://index.docker.io/cyanautomation/motioninocean:vX.Y \
  --repo CyanAutomation/motioninocean \
  --signer-workflow CyanAutomation/motioninocean/.github/workflows/docker-publish.yml \
  --bundle-from-oci
```

Replace `X.Y` with the release version without the leading `v`.

## Sources

- [`.github/workflows/docker-publish.yml`](../../.github/workflows/docker-publish.yml) — Verification and container image publishing after a GitHub Release is published.
- [`docs/CHANGELOG.md`](../CHANGELOG.md) — User-facing release notes.
- [GitHub CLI attestation verification](https://cli.github.com/manual/gh_attestation_verify) — Container image verification options.
