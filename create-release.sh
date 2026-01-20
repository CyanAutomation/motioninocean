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


# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 motion-in-ocean Release Creator${NC}"
echo "======================================"
echo -e "Releasing from branch: ${GREEN}${CURRENT_BRANCH}${NC}"
echo ""

# Check if VERSION file exists
if [ ! -f "${VERSION_FILE}" ]; then
    echo -e "${RED}❌ VERSION file not found${NC}"
    exit 1
fi

# Read current version
CURRENT_VERSION=$(cat "${VERSION_FILE}")
echo -e "Current version: ${GREEN}${CURRENT_VERSION}${NC}"
echo ""

# Ask for new version
echo -e "${YELLOW}Enter new version (e.g., 1.0.1, 1.1.0, 2.0.0):${NC}"
read -r NEW_VERSION

# Validate version format (basic semver check)
if ! [[ "${NEW_VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${RED}❌ Invalid version format. Use semantic versioning (e.g., 1.0.0)${NC}"
    exit 1
fi

echo ""
echo -e "New version will be: ${GREEN}v${NEW_VERSION}${NC}"
echo ""

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}❌ You have uncommitted changes.${NC}"
    echo "Please commit or stash them before creating a release."
    echo ""
    git status --short
    echo ""
    exit 1
fi

# Update VERSION file
echo "${NEW_VERSION}" > "${VERSION_FILE}"
echo -e "${GREEN}✓${NC} Updated ${VERSION_FILE}"

# Update CHANGELOG
TODAY=$(date +%Y-%m-%d)
CHANGELOG_ENTRY="## [${NEW_VERSION}] - ${TODAY}"

# Get the latest tag. If no tags, use the first commit
LATEST_TAG=$(git describe --tags `git rev-list --tags --max-count=1` --abbrev=0 2>/dev/null)

if [ -z "$LATEST_TAG" ]; then
    echo -e "${YELLOW}⚠️  No tags found. Generating changelog from all commits.${NC}"
    # Get all commits if no tags are found
    COMMIT_LOG=$(git log --pretty=format:"- %s")
else
    echo -e "Generating changelog from commits since ${GREEN}${LATEST_TAG}${NC}"
    COMMIT_LOG=$(git log --pretty=format:"- %s" "${LATEST_TAG}"..HEAD)
fi

if [ -z "$COMMIT_LOG" ]; then
    COMMIT_LOG="- No changes to log."
fi

if grep -q "## \[Unreleased\]" "${CHANGELOG_FILE}"; then
    # Create a temp file with the changelog entry to avoid issues with special characters in sed
    CHANGELOG_BODY=$(mktemp)
    # The empty line before the entry is important for markdown formatting
    echo -e "\n${CHANGELOG_ENTRY}\n" >> "${CHANGELOG_BODY}"
    echo -e "${COMMIT_LOG}" >> "${CHANGELOG_BODY}"

    # Use sed to insert the content of the temp file after the '[Unreleased]' line
    sed -i -e "/## \[Unreleased\]/r ${CHANGELOG_BODY}" "${CHANGELOG_FILE}"

    rm "${CHANGELOG_BODY}"
    echo -e "${GREEN}✓${NC} Updated ${CHANGELOG_FILE}"
else
    echo -e "${YELLOW}⚠️  Could not find '## [Unreleased]' in CHANGELOG.md. Please update manually.${NC}"
fi

echo ""
echo -e "${BLUE}📝 Release Summary:${NC}"
echo "-----------------------------------"
echo -e "Version: ${GREEN}v${NEW_VERSION}${NC}"
echo -e "Date: ${TODAY}"
echo ""

# Show what will be committed
echo -e "${BLUE}Files to commit:${NC}"
git diff --name-only "${VERSION_FILE}" "${CHANGELOG_FILE}" 2>/dev/null || echo "  ${VERSION_FILE}"
echo ""

# Confirm release
echo -e "${YELLOW}Ready to create release v${NEW_VERSION}? This will:${NC}"
echo "  1. Commit VERSION and CHANGELOG updates"
echo "  2. Create and push git tag v${NEW_VERSION}"
echo "  3. Trigger GitHub Actions to build and publish Docker image"
echo ""
echo -e "${YELLOW}Continue? (y/N):${NC}"
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
echo -e "${BLUE}Committing changes...${NC}"
git add "${VERSION_FILE}" "${CHANGELOG_FILE}"
git commit -m "Release v${NEW_VERSION}"
echo -e "${GREEN}✓${NC} Changes committed"

# Create tag
echo -e "${BLUE}Creating tag v${NEW_VERSION}...${NC}"
git tag -a "v${NEW_VERSION}" -m "Release v${NEW_VERSION}"
echo -e "${GREEN}✓${NC} Tag created"

# Push changes and tag
echo -e "${BLUE}Pushing to remote...${NC}"
if git push origin "${CURRENT_BRANCH}"; then
    echo -e "${GREEN}✓${NC} Pushed changes to ${CURRENT_BRANCH} branch."
else
    echo -e "${RED}❌ Failed to push changes to ${CURRENT_BRANCH} branch.${NC}"
    echo -e "${YELLOW}To revert the local commit, run: git reset --hard HEAD~1${NC}"
    exit 1
fi

if git push origin "v${NEW_VERSION}"; then
    echo -e "${GREEN}✓${NC} Pushed tag v${NEW_VERSION} to remote."
else
    echo -e "${RED}❌ Failed to push tag to remote.${NC}"
    echo -e "${YELLOW}To remove the local tag, run: git tag -d v${NEW_VERSION}${NC}"
    exit 1
fi

# Update 'latest' tag to point to this release
echo -e "${BLUE}Updating 'latest' tag...${NC}"
git tag -f latest
if git push -f origin latest; then
    echo -e "${GREEN}✓${NC} Updated 'latest' tag to point to v${NEW_VERSION}."
else
    echo -e "${RED}❌ Failed to push 'latest' tag.${NC}"
    echo -e "${YELLOW}This is not critical, but you may want to manually run: git push -f origin latest${NC}"
fi

echo ""
echo -e "${BLUE}⏳ Waiting for GitHub Actions workflow to start...${NC}"
echo "This ensures the Docker image is built and published before completing."
echo ""

# Function to check if gh CLI is available
check_gh_cli() {
    if ! command -v gh &> /dev/null; then
        echo -e "${YELLOW}⚠️  GitHub CLI (gh) is not installed.${NC}"
        echo "Workflow verification requires the GitHub CLI."
        echo "Install it from: https://cli.github.com/"
        echo ""
        echo -e "${YELLOW}Skipping workflow verification. Please manually check:${NC}"
        echo "  https://github.com/${REPO_SLUG}/actions"
        return 1
    fi
    
    # Check if gh is authenticated
    if ! gh auth status &> /dev/null; then
        echo -e "${YELLOW}⚠️  GitHub CLI is not authenticated.${NC}"
        echo "Please run: gh auth login"
        echo ""
        echo -e "${YELLOW}Skipping workflow verification. Please manually check:${NC}"
        echo "  https://github.com/${REPO_SLUG}/actions"
        return 1
    fi
    
    return 0
}

# Function to rollback the release
rollback_release() {
    echo ""
    echo -e "${RED}❌ Workflow failed or was cancelled.${NC}"
    echo -e "${YELLOW}Rolling back release v${NEW_VERSION}...${NC}"
    echo ""
    
    # Delete remote tags
    echo -e "${BLUE}Deleting remote tags...${NC}"
    if git push origin --delete "v${NEW_VERSION}" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Deleted remote tag v${NEW_VERSION}"
    else
        echo -e "${YELLOW}⚠️  Could not delete remote tag v${NEW_VERSION} (may not exist)${NC}"
    fi
    
    # Delete local tags
    echo -e "${BLUE}Deleting local tags...${NC}"
    if git tag -d "v${NEW_VERSION}" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Deleted local tag v${NEW_VERSION}"
    else
        echo -e "${YELLOW}⚠️  Could not delete local tag v${NEW_VERSION}${NC}"
    fi
    
    # Reset to previous commit
    echo -e "${BLUE}Reverting release commit...${NC}"
    if git reset --hard HEAD~1; then
        echo -e "${GREEN}✓${NC} Reverted local commit"
    else
        echo -e "${RED}❌ Failed to revert local commit${NC}"
    fi
    
    # Force push to remote to remove the commit
    echo -e "${BLUE}Removing commit from remote...${NC}"
    if git push -f origin "${CURRENT_BRANCH}"; then
        echo -e "${GREEN}✓${NC} Removed commit from remote"
    else
        echo -e "${RED}❌ Failed to remove commit from remote${NC}"
        echo -e "${YELLOW}You may need to manually revert: git push -f origin ${CURRENT_BRANCH}${NC}"
    fi
    
    # Restore VERSION and CHANGELOG files
    echo -e "${BLUE}Restoring VERSION and CHANGELOG files...${NC}"
    git checkout HEAD -- "${VERSION_FILE}" "${CHANGELOG_FILE}" 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Restored files"
    
    echo ""
    echo -e "${RED}🔄 Release rollback complete.${NC}"
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
            echo -e "${GREEN}✓${NC} Found workflow run: ${WORKFLOW_RUN_ID}"
            break
        fi
        
        echo "  Waiting for workflow to start... (${ELAPSED}s elapsed)"
        sleep $POLL_INTERVAL
        ELAPSED=$((ELAPSED + POLL_INTERVAL))
    done
    
    if [ -z "${WORKFLOW_RUN_ID}" ]; then
        echo -e "${YELLOW}⚠️  Could not find workflow run after ${MAX_WAIT_MINUTES} minutes.${NC}"
        echo "The workflow may not have been triggered or may be delayed."
        echo ""
        echo -e "${YELLOW}Please manually verify the workflow:${NC}"
        echo "  https://github.com/${REPO_SLUG}/actions"
        echo ""
        echo -e "${YELLOW}Would you like to rollback this release? (y/N):${NC}"
        read -r ROLLBACK_CONFIRM
        if [[ "${ROLLBACK_CONFIRM}" =~ ^[Yy]$ ]]; then
            rollback_release
        else
            echo "Continuing without verification. Please check the workflow manually."
        fi
    else
        # Monitor the workflow
        echo ""
        echo -e "${BLUE}📊 Monitoring workflow progress...${NC}"
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
                        echo -e "${GREEN}✅ Workflow completed successfully!${NC}"
                        echo ""
                        echo -e "${BLUE}Docker image published:${NC}"
                        echo "  ghcr.io/${REPO_SLUG,,}:${NEW_VERSION}"
                        echo "  ghcr.io/${REPO_SLUG,,}:latest"
                        echo ""
                        echo -e "${BLUE}Next steps:${NC}"
                        echo "  1. Pull the new image: docker pull ghcr.io/${REPO_SLUG,,}:${NEW_VERSION}"
                        echo "  2. View the workflow: https://github.com/${REPO_SLUG}/actions/runs/${WORKFLOW_RUN_ID}"
                        echo "  3. GitHub Release was created automatically: https://github.com/${REPO_SLUG}/releases/tag/v${NEW_VERSION}"
                        echo ""
                        echo -e "${GREEN}✅ Release v${NEW_VERSION} completed successfully!${NC}"
                        exit 0
                    else
                        rollback_release
                    fi
                    ;;
                "in_progress"|"queued"|"pending"|"waiting")
                    echo -ne "  Status: ${WORKFLOW_STATUS} (${ELAPSED}s elapsed)\r"
                    ;;
                *)
                    echo -e "${RED}❌ Workflow status: ${WORKFLOW_STATUS}${NC}"
                    rollback_release
                    ;;
            esac
            
            sleep $POLL_INTERVAL
            ELAPSED=$((ELAPSED + POLL_INTERVAL))
        done
        
        # Timeout reached
        echo ""
        echo -e "${YELLOW}⚠️  Workflow did not complete within ${MAX_WAIT_MINUTES} minutes.${NC}"
        echo "Current status: ${WORKFLOW_STATUS}"
        echo ""
        echo -e "${YELLOW}Would you like to rollback this release? (y/N):${NC}"
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
    echo -e "${BLUE}Docker image will be available at:${NC}"
    echo "  ghcr.io/${REPO_SLUG,,}:${NEW_VERSION}"
    echo "  ghcr.io/${REPO_SLUG,,}:latest"
    echo ""
    echo -e "${GREEN}✅ Release v${NEW_VERSION} created!${NC}"
    echo "Please manually verify the workflow completes successfully."
fi

echo ""
