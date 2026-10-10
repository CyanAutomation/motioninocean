#!/usr/bin/env bash
# Print the changelog section for a release version, or the standard fallback.

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 VERSION CHANGELOG_FILE" >&2
    exit 64
fi

VERSION=$1
CHANGELOG_FILE=$2
FALLBACK="Release ${VERSION} - See commit history for details."

if [[ ! -f "${CHANGELOG_FILE}" ]]; then
    echo "Warning: ${CHANGELOG_FILE} not found" >&2
    printf '%s\n' "${FALLBACK}"
    exit 0
fi

CHANGELOG_CONTENT=$(awk -v header="## [${VERSION}]" '
    index($0, header) == 1 { found = 1; next }
    found && /^## \[/ { exit }
    found { print }
' "${CHANGELOG_FILE}" | sed '/^[[:space:]]*$/d')

if [[ -z "${CHANGELOG_CONTENT}" ]]; then
    echo "Warning: No changelog section found for ${VERSION}" >&2
    printf '%s\n' "${FALLBACK}"
else
    printf '%s\n' "${CHANGELOG_CONTENT}"
fi
