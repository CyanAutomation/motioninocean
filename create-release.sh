#!/bin/bash
# create-release.sh - Create a new release for motion-in-ocean
# This script helps tag and prepare a release

set -e

VERSION_FILE="VERSION"
CHANGELOG_FILE="CHANGELOG.md"

# Determine the current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Get remote URL to build GitHub links
REMOTE_URL=$(git remote get-url origin)
# transform ssh or https urls into "owner/repo"
REPO_SLUG=$(echo "${REMOTE_URL}" | sed -E 's/.*(github.com:|github.com\/)//; s/\.git$//')



echo "[INFO] motion-in-ocean Release Creator"
echo "======================================"
echo "Releasing from branch: ${CURRENT_BRANCH}"
echo ""

# Check if VERSION file exists
if [ ! -f "${VERSION_FILE}" ]; then
    echo "[ERROR] VERSION file not found"
    exit 1
fi

# Read current version
CURRENT_VERSION=$(cat "${VERSION_FILE}")
echo "Current version: ${CURRENT_VERSION}"
echo ""

# Ask for new version
echo "[INFO] Enter new version (e.g., 1.0.1, 1.1.0, 2.0.0):"
read -r NEW_VERSION

# Validate version format (basic semver check)
if ! [[ "${NEW_VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "[ERROR] Invalid version format. Use semantic versioning (e.g., 1.0.0)"
    exit 1
fi

echo ""
echo "New version will be: v${NEW_VERSION}"
echo ""

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "[ERROR] You have uncommitted changes."
    echo "Please commit or stash them before creating a release."
    echo ""
    git status --short
    echo ""
    exit 1
fi

# Update VERSION file
echo "${NEW_VERSION}" > "${VERSION_FILE}"
echo "[INFO] Updated ${VERSION_FILE}"

# Update CHANGELOG
TODAY=$(date +%Y-%m-%d)
CHANGELOG_ENTRY="## [${NEW_VERSION}] - ${TODAY}"

# Get the latest tag. If no tags, use the first commit
LATEST_TAG=$(git describe --tags "$(git rev-list --tags --max-count=1)" --abbrev=0 2>/dev/null)

if [ -z "$LATEST_TAG" ]; then
    echo "[WARN] No tags found. Generating changelog from all commits."
    # Get all commits if no tags are found
    COMMIT_LOG=$(git log --pretty=format:"- %s")
else
    echo "Generating changelog from commits since ${LATEST_TAG}"
    COMMIT_LOG=$(git log --pretty=format:"- %s" "${LATEST_TAG}"..HEAD)
fi

if [ -z "$COMMIT_LOG" ]; then
    COMMIT_LOG="- No changes to log."
fi

if grep -q "## \[Unreleased\]" "${CHANGELOG_FILE}"; then
    # Create a temp file with the changelog entry to avoid issues with special characters in sed
    CHANGELOG_BODY=$(mktemp)
    # The empty line before the entry is important for markdown formatting
    printf "\n%s\n\n" "${CHANGELOG_ENTRY}" >> "${CHANGELOG_BODY}"
    echo "${COMMIT_LOG}" >> "${CHANGELOG_BODY}"

    # Use sed to insert the content of the temp file after the '[Unreleased]' line
    sed -i -e "/## \[Unreleased\]/r ${CHANGELOG_BODY}" "${CHANGELOG_FILE}"

    rm "${CHANGELOG_BODY}"
    echo "[INFO] Updated ${CHANGELOG_FILE}"
else
    echo "[WARN] Could not find '## [Unreleased]' in CHANGELOG.md. Please update manually."
fi

echo ""
echo "[INFO] Release summary:"
echo "-----------------------------------"
echo "Version: v${NEW_VERSION}"
echo "Date: ${TODAY}"
echo ""

# Show what will be committed
echo "[INFO] Files to commit:"
git diff --name-only "${VERSION_FILE}" "${CHANGELOG_FILE}" 2>/dev/null || echo "  ${VERSION_FILE}"
echo ""

# Confirm release
echo "[INFO] Ready to create release v${NEW_VERSION}? This will:"
echo "  1. Commit VERSION and CHANGELOG updates"
echo "  2. Create and push git tag v${NEW_VERSION}"
echo "  3. Trigger GitHub Actions to build and publish Docker image"
echo ""
echo "[INFO] Continue? (y/N):"
read -r CONFIRM

if [[ ! "${CONFIRM}" =~ ^[Yy]$ ]]; then
    echo "Release cancelled."
    # Restore modified files
    git checkout -- "${VERSION_FILE}" "${CHANGELOG_FILE}"
    echo "Reverted changes to ${VERSION_FILE} and ${CHANGELOG_FILE}."
    exit 0
fi

# Commit changes
echo ""
echo "[INFO] Committing changes..."
git add "${VERSION_FILE}" "${CHANGELOG_FILE}"
git commit -m "Release v${NEW_VERSION}"
echo "[INFO] Changes committed"

# Create tag
echo "[INFO] Creating tag v${NEW_VERSION}..."
git tag -a "v${NEW_VERSION}" -m "Release v${NEW_VERSION}"
echo "[INFO] Tag created"

# Push changes and tag
echo "[INFO] Pushing to remote..."
if git push origin "${CURRENT_BRANCH}"; then
    echo "[INFO] Pushed changes to ${CURRENT_BRANCH} branch."
else
    echo "[ERROR] Failed to push changes to ${CURRENT_BRANCH} branch."
    echo "[INFO] To revert the local commit, run: git reset --hard HEAD~1"
    exit 1
fi

if git push origin "v${NEW_VERSION}"; then
    echo "[INFO] Pushed tag v${NEW_VERSION} to remote."
else
    echo "[ERROR] Failed to push tag to remote."
    echo "[INFO] To remove the local tag, run: git tag -d v${NEW_VERSION}"
    exit 1
fi

# Update 'latest' tag to point to this release
echo "[INFO] Updating 'latest' tag..."
git tag -f latest
if git push -f origin latest; then
    echo "[INFO] Updated 'latest' tag to point to v${NEW_VERSION}."
else
    echo "[ERROR] Failed to push 'latest' tag."
    echo "[INFO] This is not critical, but you may want to manually run: git push -f origin latest"
fi

echo ""
echo "[INFO] Waiting for GitHub Actions workflow to start..."
echo "This ensures the Docker image is built and published before completing."
echo ""

# Function to check if gh CLI is available
check_gh_cli() {
    if ! command -v gh &> /dev/null; then
        echo "[WARN] GitHub CLI (gh) is not installed."
        echo "Workflow verification requires the GitHub CLI."
        echo "Install it from: https://cli.github.com/"
        echo ""
        echo "[INFO] Skipping workflow verification. Please manually check:"
        echo "  https://github.com/${REPO_SLUG}/actions"
        return 1
    fi
    
    # Check if gh is authenticated
    if ! gh auth status &> /dev/null; then
        echo "[WARN] GitHub CLI is not authenticated."
        echo "Please run: gh auth login"
        echo ""
        echo "[INFO] Skipping workflow verification. Please manually check:"
        echo "  https://github.com/${REPO_SLUG}/actions"
        return 1
    fi
    
    return 0
}

# Function to rollback the release
rollback_release() {
    echo ""
    echo "[ERROR] Workflow failed or was cancelled."
    echo "[INFO] Rolling back release v${NEW_VERSION}..."
    echo ""
    
    # Delete remote tags
    echo "[INFO] Deleting remote tags..."
    if git push origin --delete "v${NEW_VERSION}" 2>/dev/null; then
        echo "[INFO] Deleted remote tag v${NEW_VERSION}"
    else
        echo "[WARN] Could not delete remote tag v${NEW_VERSION} (may not exist)"
    fi
    
    # Delete local tags
    echo "[INFO] Deleting local tags..."
    if git tag -d "v${NEW_VERSION}" 2>/dev/null; then
        echo "[INFO] Deleted local tag v${NEW_VERSION}"
    else
        echo "[WARN] Could not delete local tag v${NEW_VERSION}"
    fi
    
    # Reset to previous commit
    echo "[INFO] Reverting release commit..."
    if git reset --hard HEAD~1; then
        echo "[INFO] Reverted local commit"
    else
        echo "[ERROR] Failed to revert local commit"
    fi
    
    # Force push to remote to remove the commit
    echo "[INFO] Removing commit from remote..."
    if git push -f origin "${CURRENT_BRANCH}"; then
        echo "[INFO] Removed commit from remote"
    else
        echo "[ERROR] Failed to remove commit from remote"
        echo "[INFO] You may need to manually revert: git push -f origin ${CURRENT_BRANCH}"
    fi
    
    # Restore VERSION and CHANGELOG files
    echo "[INFO] Restoring VERSION and CHANGELOG files..."
    git checkout HEAD -- "${VERSION_FILE}" "${CHANGELOG_FILE}" 2>/dev/null || true
    echo "[INFO] Restored files"
    
    echo ""
    echo "[ERROR] Release rollback complete."
    echo "The repository has been restored to its state before the release."
    exit 1
}

# Check if gh CLI is available and authenticated
if check_gh_cli; then
    # Wait a few seconds for the workflow to be triggered
    sleep 5
    
    # Find the workflow run for this tag
    WORKFLOW_NAME="Build and publish Docker image"
    MAX_WAIT_MINUTES=15
    MAX_WAIT_SECONDS=$((MAX_WAIT_MINUTES * 60))
    POLL_INTERVAL=10
    ELAPSED=0
    
    echo "Searching for workflow run (timeout: ${MAX_WAIT_MINUTES} minutes)..."
    
    WORKFLOW_RUN_ID=""
    while [ $ELAPSED -lt $MAX_WAIT_SECONDS ]; do
        # Get the latest workflow run for this tag
        WORKFLOW_RUN_ID=$(gh run list \
            --repo "${REPO_SLUG}" \
            --workflow "${WORKFLOW_NAME}" \
            --json databaseId,headBranch,conclusion,status \
            --jq ".[] | select(.headBranch == \"v${NEW_VERSION}\") | .databaseId" \
            --limit 1 2>/dev/null | head -1)
        
        if [ -n "${WORKFLOW_RUN_ID}" ]; then
            echo "[INFO] Found workflow run: ${WORKFLOW_RUN_ID}"
            break
        fi
        
        echo "  Waiting for workflow to start... (${ELAPSED}s elapsed)"
        sleep $POLL_INTERVAL
        ELAPSED=$((ELAPSED + POLL_INTERVAL))
    done
    
    if [ -z "${WORKFLOW_RUN_ID}" ]; then
        echo "[WARN] Could not find workflow run after ${MAX_WAIT_MINUTES} minutes."
        echo "The workflow may not have been triggered or may be delayed."
        echo ""
        echo "[INFO] Please manually verify the workflow:"
        echo "  https://github.com/${REPO_SLUG}/actions"
        echo ""
        echo "[INFO] Would you like to rollback this release? (y/N):"
        read -r ROLLBACK_CONFIRM
        if [[ "${ROLLBACK_CONFIRM}" =~ ^[Yy]$ ]]; then
            rollback_release
        else
            echo "Continuing without verification. Please check the workflow manually."
        fi
    else
        # Monitor the workflow
        echo ""
        echo "[INFO] Monitoring workflow progress..."
        echo "View detailed logs: https://github.com/${REPO_SLUG}/actions/runs/${WORKFLOW_RUN_ID}"
        echo ""
        
        WORKFLOW_STATUS=""
        ELAPSED=0
        while [ $ELAPSED -lt $MAX_WAIT_SECONDS ]; do
            # Get workflow status
            WORKFLOW_DATA=$(gh run view "${WORKFLOW_RUN_ID}" \
                --repo "${REPO_SLUG}" \
                --json status,conclusion 2>/dev/null)
            
            WORKFLOW_STATUS=$(echo "${WORKFLOW_DATA}" | jq -r '.status')
            WORKFLOW_CONCLUSION=$(echo "${WORKFLOW_DATA}" | jq -r '.conclusion')
            
            case "${WORKFLOW_STATUS}" in
                "completed")
                    echo ""
                    if [ "${WORKFLOW_CONCLUSION}" = "success" ]; then
                        echo "[INFO] Workflow completed successfully!"
                        echo ""
                        echo "[INFO] Docker image published:"
                        echo "  ghcr.io/${REPO_SLUG,,}:${NEW_VERSION}"
                        echo "  ghcr.io/${REPO_SLUG,,}:latest"
                        echo ""
                        echo "[INFO] Next steps:"
                        echo "  1. Pull the new image: docker pull ghcr.io/${REPO_SLUG,,}:${NEW_VERSION}"
                        echo "  2. View the workflow: https://github.com/${REPO_SLUG}/actions/runs/${WORKFLOW_RUN_ID}"
                        echo "  3. GitHub Release was created automatically: https://github.com/${REPO_SLUG}/releases/tag/v${NEW_VERSION}"
                        echo ""
                        echo "[INFO] Release v${NEW_VERSION} completed successfully!"
                        exit 0
                    else
                        rollback_release
                    fi
                    ;;
                "in_progress"|"queued"|"pending"|"waiting")
                    echo -ne "  Status: ${WORKFLOW_STATUS} (${ELAPSED}s elapsed)\r"
                    ;;
                *)
                    echo "[ERROR] Workflow status: ${WORKFLOW_STATUS}"
                    rollback_release
                    ;;
            esac
            
            sleep $POLL_INTERVAL
            ELAPSED=$((ELAPSED + POLL_INTERVAL))
        done
        
        # Timeout reached
        echo ""
        echo "[WARN] Workflow did not complete within ${MAX_WAIT_MINUTES} minutes."
        echo "Current status: ${WORKFLOW_STATUS}"
        echo ""
        echo "[INFO] Would you like to rollback this release? (y/N):"
        read -r ROLLBACK_CONFIRM
        if [[ "${ROLLBACK_CONFIRM}" =~ ^[Yy]$ ]]; then
            rollback_release
        else
            echo "Continuing without verification. Please check the workflow manually:"
            echo "  https://github.com/${REPO_SLUG}/actions/runs/${WORKFLOW_RUN_ID}"
        fi
    fi
else
    # gh CLI not available
    echo "[INFO] Docker image will be available at:"
    echo "  ghcr.io/${REPO_SLUG,,}:${NEW_VERSION}"
    echo "  ghcr.io/${REPO_SLUG,,}:latest"
    echo ""
    echo "[INFO] Release v${NEW_VERSION} created!"
    echo "Please manually verify the workflow completes successfully."
fi

echo ""
