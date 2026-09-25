#!/usr/bin/env bash
# Prepare and publish a semantic-version release from main.

set -euo pipefail

VERSION_FILE="VERSION"
CHANGELOG_FILE="docs/CHANGELOG.md"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
REMOTE_URL=$(git remote get-url origin)
REPO_SLUG=$(echo "${REMOTE_URL}" | sed -E 's/.*(github.com:|github.com\/)//; s/\.git$//')

echo "[INFO] motion-in-ocean Release Creator"
echo "======================================"

if [[ "${CURRENT_BRANCH}" != "main" ]]; then
    echo "[ERROR] Releases must be prepared from main (current branch: ${CURRENT_BRANCH})." >&2
    exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
    echo "[ERROR] The working tree must be clean before creating a release." >&2
    git status --short
    exit 1
fi

if [[ ! -f "${VERSION_FILE}" || ! -f "${CHANGELOG_FILE}" ]]; then
    echo "[ERROR] Required release files are missing: ${VERSION_FILE}, ${CHANGELOG_FILE}." >&2
    exit 1
fi

CURRENT_VERSION=$(cat "${VERSION_FILE}")
echo "Current version: ${CURRENT_VERSION}"
echo "Enter the new version (MAJOR.MINOR.PATCH):"
read -r NEW_VERSION

if ! [[ "${NEW_VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "[ERROR] Use a semantic version such as 1.2.3." >&2
    exit 1
fi

if [[ "${NEW_VERSION}" == "${CURRENT_VERSION}" ]]; then
    echo "[ERROR] The new version must differ from ${CURRENT_VERSION}." >&2
    exit 1
fi

if git show-ref --verify --quiet "refs/tags/v${NEW_VERSION}"; then
    echo "[ERROR] Tag v${NEW_VERSION} already exists locally." >&2
    exit 1
fi

if ! grep -Fq '## [Unreleased]' "${CHANGELOG_FILE}"; then
    echo "[ERROR] ${CHANGELOG_FILE} must contain an '## [Unreleased]' section." >&2
    exit 1
fi

TODAY=$(date +%Y-%m-%d)
LATEST_TAG=$(git describe --tags "$(git rev-list --tags --max-count=1)" --abbrev=0 2>/dev/null || true)
if [[ -n "${LATEST_TAG}" ]]; then
    COMMIT_LOG=$(git log --pretty=format:"- %s" "${LATEST_TAG}"..HEAD)
else
    COMMIT_LOG=$(git log --pretty=format:"- %s")
fi
if [[ -z "${COMMIT_LOG}" ]]; then
    COMMIT_LOG="- No changes to log."
fi

CHANGELOG_ENTRY="## [${NEW_VERSION}] - ${TODAY}"
echo "${NEW_VERSION}" > "${VERSION_FILE}"
python3 - "${CHANGELOG_FILE}" "${CHANGELOG_ENTRY}" "${COMMIT_LOG}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
marker = "## [Unreleased]"
section = f"{marker}\n\n{sys.argv[2]}\n\n{sys.argv[3]}\n"
path.write_text(text.replace(marker, section, 1), encoding="utf-8")
PY

echo ""
echo "[INFO] Release v${NEW_VERSION} will:"
echo "  1. Commit ${VERSION_FILE} and ${CHANGELOG_FILE} on main"
echo "  2. Create and push tag v${NEW_VERSION}"
echo "  3. Trigger GitHub Actions to build and publish the container images"
echo "  4. Leave the release commit and tag in place if publication fails"
echo "The workflow creates the mutable latest image tag; this script does not force-update Git refs."
echo "Continue? (y/N):"
read -r CONFIRM

if [[ ! "${CONFIRM}" =~ ^[Yy]$ ]]; then
    git restore -- "${VERSION_FILE}" "${CHANGELOG_FILE}"
    echo "Release cancelled; generated file changes were restored."
    exit 0
fi

git add -- "${VERSION_FILE}" "${CHANGELOG_FILE}"
git commit -m "Release v${NEW_VERSION}"
git tag -a "v${NEW_VERSION}" -m "Release v${NEW_VERSION}"

if ! git push origin main; then
    echo "[ERROR] Could not push the release commit. The local commit and tag are retained." >&2
    echo "Inspect the branch, then push main and v${NEW_VERSION} after resolving the cause." >&2
    exit 1
fi

if ! git push origin "v${NEW_VERSION}"; then
    echo "[ERROR] Could not push v${NEW_VERSION}. The local commit and tag are retained." >&2
    echo "Inspect the remote, then push the tag after resolving the cause." >&2
    exit 1
fi

echo "[INFO] Pushed main and tag v${NEW_VERSION}."

check_gh_cli() {
    if ! command -v gh >/dev/null 2>&1; then
        echo "[WARN] GitHub CLI is not installed; verify the release workflow manually."
        return 1
    fi
    if ! gh auth status >/dev/null 2>&1; then
        echo "[WARN] GitHub CLI is not authenticated; verify the release workflow manually."
        return 1
    fi
    return 0
}

if ! check_gh_cli; then
    echo "Actions: https://github.com/${REPO_SLUG}/actions"
    echo "Release: https://github.com/${REPO_SLUG}/releases/tag/v${NEW_VERSION}"
    exit 0
fi

WORKFLOW_NAME="Build and publish Docker image"
MAX_WAIT_SECONDS=$((20 * 60))
POLL_INTERVAL=10
ELAPSED=0
WORKFLOW_RUN_ID=""

echo "[INFO] Waiting for the release workflow (up to 20 minutes)..."
while [[ ${ELAPSED} -lt ${MAX_WAIT_SECONDS} ]]; do
    WORKFLOW_RUN_ID=$(gh run list \
        --repo "${REPO_SLUG}" \
        --workflow "${WORKFLOW_NAME}" \
        --json databaseId,headBranch \
        --jq ".[] | select(.headBranch == \"v${NEW_VERSION}\") | .databaseId" \
        --limit 10 2>/dev/null | head -1)
    [[ -n "${WORKFLOW_RUN_ID}" ]] && break
    sleep "${POLL_INTERVAL}"
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

if [[ -z "${WORKFLOW_RUN_ID}" ]]; then
    echo "[ERROR] No workflow run found for v${NEW_VERSION}. The commit and tag remain published." >&2
    echo "Check https://github.com/${REPO_SLUG}/actions and trigger or diagnose the workflow manually." >&2
    exit 1
fi

echo "[INFO] Monitoring workflow run ${WORKFLOW_RUN_ID}."
ELAPSED=0
while [[ ${ELAPSED} -lt ${MAX_WAIT_SECONDS} ]]; do
    WORKFLOW_DATA=$(gh run view "${WORKFLOW_RUN_ID}" \
        --repo "${REPO_SLUG}" \
        --json status,conclusion \
        --jq '[.status, .conclusion] | @tsv')
    IFS=$'\t' read -r WORKFLOW_STATUS WORKFLOW_CONCLUSION <<< "${WORKFLOW_DATA}"

    if [[ "${WORKFLOW_STATUS}" == "completed" ]]; then
        if [[ "${WORKFLOW_CONCLUSION}" == "success" ]]; then
            echo "[INFO] Release v${NEW_VERSION} published successfully."
            echo "  ghcr.io/${REPO_SLUG,,}:${NEW_VERSION}"
            echo "  ghcr.io/${REPO_SLUG,,}:latest"
            echo "  https://github.com/${REPO_SLUG}/releases/tag/v${NEW_VERSION}"
            exit 0
        fi
        echo "[ERROR] Release workflow concluded ${WORKFLOW_CONCLUSION}. The commit and tag remain published." >&2
        echo "Inspect https://github.com/${REPO_SLUG}/actions/runs/${WORKFLOW_RUN_ID} before deciding on recovery." >&2
        exit 1
    fi

    sleep "${POLL_INTERVAL}"
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

echo "[ERROR] Release workflow did not complete within 20 minutes. The commit and tag remain published." >&2
echo "Inspect https://github.com/${REPO_SLUG}/actions/runs/${WORKFLOW_RUN_ID} before deciding on recovery." >&2
exit 1
