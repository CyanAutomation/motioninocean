#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${IMAGE_REF:-}" ]]; then
  echo "::error title=Candidate image missing::IMAGE_REF must identify the scanned candidate image."
  exit 1
fi
if [[ -z "${DOCKER_METADATA_TAGS:-}" ]]; then
  echo "::error title=Production image tags missing::DOCKER_METADATA_TAGS is empty."
  exit 1
fi
if [[ -z "${GITHUB_OUTPUT:-}" ]]; then
  echo "::error title=Workflow output missing::GITHUB_OUTPUT is required."
  exit 1
fi

INSPECT_MAX_ATTEMPTS="${INSPECT_MAX_ATTEMPTS:-4}"
INSPECT_RETRY_BASE_DELAY_SECONDS="${INSPECT_RETRY_BASE_DELAY_SECONDS:-2}"
if [[ ! "$INSPECT_MAX_ATTEMPTS" =~ ^[1-9][0-9]*$ ]]; then
  echo "::error title=Invalid retry configuration::INSPECT_MAX_ATTEMPTS must be a positive integer."
  exit 1
fi
if [[ ! "$INSPECT_RETRY_BASE_DELAY_SECONDS" =~ ^[0-9]+$ ]]; then
  echo "::error title=Invalid retry configuration::INSPECT_RETRY_BASE_DELAY_SECONDS must be a non-negative integer."
  exit 1
fi

tmp_dir="${RUNNER_TEMP:-${TMPDIR:-/tmp}}"
mkdir -p "$tmp_dir"
candidate_manifest_file="$(mktemp "$tmp_dir/mio-candidate-manifest.XXXXXX")"
published_manifest_file="$(mktemp "$tmp_dir/mio-published-manifest.XXXXXX")"
metadata_file="$(mktemp "$tmp_dir/mio-image-metadata.XXXXXX")"
inspect_error_file="$(mktemp "$tmp_dir/mio-inspect-error.XXXXXX")"
parse_error_file="$(mktemp "$tmp_dir/mio-parse-error.XXXXXX")"
candidate_platforms_file="$(mktemp "$tmp_dir/mio-candidate-platforms.XXXXXX")"
published_platforms_file="$(mktemp "$tmp_dir/mio-published-platforms.XXXXXX")"
trap 'rm -f "$candidate_manifest_file" "$published_manifest_file" "$metadata_file" "$inspect_error_file" "$parse_error_file" "$candidate_platforms_file" "$published_platforms_file"' EXIT

inspect_raw_manifest() {
  local reference="$1"
  local output_file="$2"
  local attempt=1
  local delay="$INSPECT_RETRY_BASE_DELAY_SECONDS"
  local status=1

  while (( attempt <= INSPECT_MAX_ATTEMPTS )); do
    echo "Inspecting $reference (attempt $attempt/$INSPECT_MAX_ATTEMPTS)"
    : > "$inspect_error_file"
    if docker buildx imagetools inspect --raw "$reference" > "$output_file" 2> "$inspect_error_file"; then
      return 0
    else
      status=$?
    fi

    echo "Inspection attempt $attempt/$INSPECT_MAX_ATTEMPTS failed for $reference (exit $status):" >&2
    cat "$inspect_error_file" >&2
    if (( attempt == INSPECT_MAX_ATTEMPTS )); then
      echo "::error title=Image manifest inspection failed::Could not inspect '$reference' after $INSPECT_MAX_ATTEMPTS attempts (exit $status)." >&2
      return 1
    fi

    if (( delay > 0 )); then
      sleep "$delay"
    fi
    if (( delay < 30 )); then
      delay=$((delay * 2))
      (( delay > 30 )) && delay=30
    fi
    attempt=$((attempt + 1))
  done
}

extract_platforms() {
  local reference="$1"
  local manifest_file="$2"
  local result_file="$3"

  if ! jq -e -c '
    [
      .manifests[]?
      | select(.platform.os == "linux" and (.platform.architecture == "amd64" or .platform.architecture == "arm64"))
      | select((.digest | type) == "string" and (.digest | test("^sha256:[0-9a-f]{64}$")))
      | {os: .platform.os, architecture: .platform.architecture, digest: .digest}
    ]
    | sort_by(.architecture)
  ' \
    "$manifest_file" > "$result_file" 2> "$parse_error_file"; then
    echo "::error title=Invalid image manifest::Could not parse the manifest for '$reference'." >&2
    cat "$parse_error_file" >&2
    return 1
  fi
}

if ! inspect_raw_manifest "$IMAGE_REF" "$candidate_manifest_file"; then
  exit 1
fi
if ! extract_platforms "$IMAGE_REF" "$candidate_manifest_file" "$candidate_platforms_file"; then
  exit 1
fi

expected_platforms='[{"os":"linux","architecture":"amd64"},{"os":"linux","architecture":"arm64"}]'
actual_platforms="$(jq -c '[.[] | {os, architecture}]' "$candidate_platforms_file")"
if [[ "$actual_platforms" != "$expected_platforms" ]]; then
  echo "::error title=Invalid candidate manifest::Candidate '$IMAGE_REF' must contain exactly linux/amd64 and linux/arm64 images." >&2
  exit 1
fi

declare -a image_tags=()
ghcr_digest=""
dockerhub_digest=""

while IFS= read -r tag; do
  [[ -n "$tag" ]] || continue

  case "$tag" in
    ghcr.io/*)
      registry="ghcr"
      ;;
    cyanautomation/*)
      registry="dockerhub"
      ;;
    *)
      echo "::error title=Unexpected production image::Unrecognized image tag '$tag'." >&2
      exit 1
      ;;
  esac

  echo "Promoting $IMAGE_REF to $tag"
  : > "$metadata_file"
  if ! docker buildx imagetools create --metadata-file "$metadata_file" --tag "$tag" "$IMAGE_REF"; then
    echo "::error title=Image promotion failed::Could not promote candidate '$IMAGE_REF' to '$tag'." >&2
    exit 1
  fi

  if ! digest="$(jq -er '."containerimage.descriptor".digest | select(test("^sha256:[0-9a-f]{64}$"))' "$metadata_file" 2> "$parse_error_file")"; then
    echo "::error title=Published image digest missing::Buildx did not return a valid target digest for '$tag'." >&2
    cat "$parse_error_file" >&2
    exit 1
  fi

  if [[ "$registry" == "ghcr" ]]; then
    if [[ -n "$ghcr_digest" && "$ghcr_digest" != "$digest" ]]; then
      echo "::error title=Production tags differ::GHCR tags point to different manifests; '$tag' has $digest." >&2
      exit 1
    fi
    ghcr_digest="$digest"
  else
    if [[ -n "$dockerhub_digest" && "$dockerhub_digest" != "$digest" ]]; then
      echo "::error title=Production tags differ::Docker Hub tags point to different manifests; '$tag' has $digest." >&2
      exit 1
    fi
    dockerhub_digest="$digest"
  fi

  image_tags+=("$tag")
done <<< "$DOCKER_METADATA_TAGS"

if [[ -z "$ghcr_digest" || -z "$dockerhub_digest" ]]; then
  echo "::error title=Production image tags missing::Expected at least one GHCR tag and one Docker Hub tag." >&2
  exit 1
fi

for tag in "${image_tags[@]}"; do
  if ! inspect_raw_manifest "$tag" "$published_manifest_file"; then
    exit 1
  fi
  if ! extract_platforms "$tag" "$published_manifest_file" "$published_platforms_file"; then
    exit 1
  fi
  if ! cmp -s "$candidate_platforms_file" "$published_platforms_file"; then
    echo "::error title=Published image differs from scanned candidate::Published platform digests do not match the scanned candidate for '$tag'." >&2
    echo "Candidate platforms: $(cat "$candidate_platforms_file")" >&2
    echo "Published platforms: $(cat "$published_platforms_file")" >&2
    exit 1
  fi
done

echo "ghcr_digest=$ghcr_digest" >> "$GITHUB_OUTPUT"
echo "dockerhub_digest=$dockerhub_digest" >> "$GITHUB_OUTPUT"
echo "Verified published manifests for ${#image_tags[@]} production tags."
