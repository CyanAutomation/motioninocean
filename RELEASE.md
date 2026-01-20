# Release Process

## Overview

This project uses an **automated, tag-driven release process** that ensures every GitHub release corresponds to a Docker image published to GHCR.

## How It Works

### Tag-Driven Workflow

```
create-release.sh → Git Tag (vX.Y.Z) → GitHub Actions → Docker Image + GitHub Release
```

1. **Developer runs** `./create-release.sh`
2. **Script prompts** for new semantic version (e.g., `1.0.1`)
3. **Script automatically:**
   - Updates `VERSION` file
   - Updates `CHANGELOG.md` with commit history
   - Creates commit: `Release vX.Y.Z`
   - Creates and pushes git tag: `vX.Y.Z`
   - Waits for GitHub Actions workflow to complete
   - Verifies Docker image was published successfully
   - **Rolls back** if workflow fails

4. **GitHub Actions workflow:**
   - Triggers on tag push (`v*.*.*`)
   - Builds Docker image for ARM64
   - Publishes to GHCR with multiple tags:
     - `vX.Y.Z` (exact tag)
     - `X.Y.Z` (semantic version)
     - `X.Y` (major.minor)
     - `latest` (if on default branch)
   - Extracts changelog content
   - Creates GitHub Release with:
     - Changelog notes
     - Docker pull instructions
     - Links to container registry

### Key Features

**✅ Guarantees:**
- Every GitHub release has a corresponding Docker image
- `latest` tag always points to the newest successful build
- Failed builds are automatically rolled back
- No manual Docker image management needed

**✅ Verification:**
- Script waits up to 15 minutes for workflow completion
- Polls GitHub Actions API for status updates
- Displays real-time progress

**✅ Rollback on Failure:**
If the workflow fails or is cancelled:
- Remote tag is deleted
- Local tag is deleted
- Release commit is reverted (local and remote)
- VERSION and CHANGELOG files are restored

## Prerequisites

### GitHub CLI (Required for Verification)

The release script uses GitHub CLI (`gh`) to monitor workflow status:

```bash
# Install GitHub CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# Authenticate
gh auth login
```

**Note:** If `gh` is not installed, the script will skip verification and you must manually check the workflow.

### Git Configuration

Ensure you have:
- Clean working directory (no uncommitted changes)
- Push access to the repository
- GitHub Actions enabled
- GHCR permissions configured (automatic with `GITHUB_TOKEN`)

## Creating a Release

### Step-by-Step

1. **Ensure clean state:**
   ```bash
   git status  # Should show "nothing to commit, working tree clean"
   ```

2. **Run release script:**
   ```bash
   ./create-release.sh
   ```

3. **Follow prompts:**
   - Enter new semantic version (e.g., `1.0.1`, `1.1.0`, `2.0.0`)
   - Review changes
   - Confirm release

4. **Monitor progress:**
   - Script pushes commit and tag
   - Waits for GitHub Actions to start
   - Shows real-time workflow status
   - Verifies successful completion

5. **Success:**
   ```
   ✅ Release v1.0.1 completed successfully!
   
   Docker image published:
     ghcr.io/hyzhak/pi-camera-in-docker:1.0.1
     ghcr.io/hyzhak/pi-camera-in-docker:latest
   
   GitHub Release created automatically:
     https://github.com/hyzhak/pi-camera-in-docker/releases/tag/v1.0.1
   ```

### What Gets Updated

**VERSION file:**
```
1.0.1
```

**CHANGELOG.md:**
```markdown
## [Unreleased]

## [1.0.1] - 2026-01-20
- Fix camera initialization bug
- Update dependencies
- Improve documentation
```

**Git:**
- Commit: `Release v1.0.1`
- Tag: `v1.0.1`
- Tag: `latest` (force-updated)

## Rollback Scenarios

### Automatic Rollback

The script automatically rolls back if:
- Workflow fails (conclusion: `failure`)
- Workflow is cancelled (conclusion: `cancelled`)
- Workflow doesn't start within 15 minutes
- Workflow doesn't complete within 15 minutes (with confirmation)

**Rollback actions:**
1. Delete remote tag `vX.Y.Z`
2. Delete local tag `vX.Y.Z`
3. Revert release commit (local)
4. Force push to remove commit from remote
5. Restore VERSION and CHANGELOG files

### Manual Rollback

If you need to manually rollback a release:

```bash
# Delete remote tag
git push origin --delete v1.0.1

# Delete local tag
git tag -d v1.0.1

# Revert commit
git reset --hard HEAD~1
git push -f origin main

# Delete GitHub Release (if created)
gh release delete v1.0.1 --repo hyzhak/pi-camera-in-docker --yes
```

## Docker Image Tags

Each release creates multiple image tags:

| Tag Format | Example | Purpose |
|------------|---------|----------|
| `vX.Y.Z` | `v1.0.1` | Exact git tag reference |
| `X.Y.Z` | `1.0.1` | Semantic version |
| `X.Y` | `1.0` | Major.minor (latest patch) |
| `latest` | `latest` | Latest stable release |

**Usage:**

```yaml
# Pin to specific version
image: ghcr.io/hyzhak/pi-camera-in-docker:1.0.1

# Track major.minor
image: ghcr.io/hyzhak/pi-camera-in-docker:1.0

# Always latest (use with caution in production)
image: ghcr.io/hyzhak/pi-camera-in-docker:latest
```

## Semantic Versioning

Follow [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (0.X.0): New features, backward compatible
- **PATCH** (0.0.X): Bug fixes, backward compatible

**Examples:**
- Bug fix: `1.0.0` → `1.0.1`
- New feature: `1.0.1` → `1.1.0`
- Breaking change: `1.1.0` → `2.0.0`

## Troubleshooting

### Workflow Doesn't Start

**Symptom:** Tag pushed but no workflow run appears

**Solutions:**
1. Check GitHub Actions is enabled
2. Verify workflow file exists: `.github/workflows/docker-publish.yml`
3. Check workflow triggers include `tags: [v*.*.*]`
4. Verify repository permissions

### Workflow Fails

**Symptom:** Workflow starts but fails during build

**Solutions:**
1. Check workflow logs: https://github.com/hyzhak/pi-camera-in-docker/actions
2. Common issues:
   - Docker build errors (check Dockerfile)
   - GHCR authentication (check GITHUB_TOKEN permissions)
   - Platform compatibility (ARM64 required)
3. Script will automatically rollback

### Image Not Appearing in GHCR

**Symptom:** Workflow succeeds but image not visible

**Solutions:**
1. Check package visibility settings
2. Verify GHCR permissions: https://github.com/hyzhak/pi-camera-in-docker/pkgs/container/pi-camera-in-docker
3. Check workflow logs for push errors
4. Ensure repository has `packages: write` permission

### Manual Verification

If you skip automatic verification:

```bash
# Check workflow status
gh run list --repo hyzhak/pi-camera-in-docker --limit 5

# View specific run
gh run view <run-id> --repo hyzhak/pi-camera-in-docker

# Verify image exists
docker pull ghcr.io/hyzhak/pi-camera-in-docker:1.0.1

# Check GitHub Release
gh release view v1.0.1 --repo hyzhak/pi-camera-in-docker
```

## FAQ

**Q: Can I create a release without running create-release.sh?**

A: Technically yes (manually create tag), but not recommended. The script handles VERSION/CHANGELOG updates, verification, and rollback.

**Q: What if I need to delete a published release?**

A: Delete the GitHub Release and git tag. The Docker image will remain in GHCR (delete manually if needed).

**Q: Can I re-use a version number?**

A: No. Once a tag is created and pushed, it's immutable. Create a new patch version instead.

**Q: How do I create a pre-release?**

A: Currently not supported by the script. Manually create tags like `v1.0.0-beta.1` if needed.

**Q: What happens to the `latest` tag on rollback?**

A: The `latest` tag is updated during the release process. On rollback, it remains pointing to the previous successful release.

## Contributing to Release Process

Improvements welcome:
- [ ] Support for pre-release versions (beta, rc)
- [ ] Dry-run mode
- [ ] Multi-arch builds (AMD64 + ARM64)
- [ ] Image security scanning integration
- [ ] Automated testing before release
- [ ] Slack/Discord notifications

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.
