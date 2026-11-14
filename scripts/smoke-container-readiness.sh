#!/usr/bin/env bash
set -euo pipefail

: "${IMAGE_REF:?Set IMAGE_REF to the local image or candidate digest}"
: "${PLATFORM:?Set PLATFORM to linux/amd64 or linux/arm64}"
SMOKE_PORT="${SMOKE_PORT:-8000}"

case "$PLATFORM" in
  linux/amd64|linux/arm64) ;;
  *)
    echo "Unsupported smoke-test platform: $PLATFORM" >&2
    exit 2
    ;;
esac

architecture="${PLATFORM#linux/}"
container_name="motion-in-ocean-smoke-${architecture}"
response_file="$(mktemp)"

cleanup() {
  docker rm --force "$container_name" >/dev/null 2>&1 || true
  rm -f "$response_file"
}
trap cleanup EXIT

docker run \
  --detach \
  --name "$container_name" \
  --platform "$PLATFORM" \
  --publish "$SMOKE_PORT:8000" \
  --env MIO_APP_MODE=webcam \
  --env MIO_MOCK_CAMERA=true \
  --env MIO_BIND_HOST=0.0.0.0 \
  --env MIO_PORT=8000 \
  "$IMAGE_REF" >/dev/null

for _ in $(seq 1 60); do
  if curl --fail --silent --output "$response_file" --max-time 3 \
    "http://127.0.0.1:${SMOKE_PORT}/ready" && \
    python3 -c \
      'import json, sys; sys.exit(json.load(open(sys.argv[1], encoding="utf-8")).get("status") != "ready")' \
      "$response_file"; then
    echo "$PLATFORM container readiness check passed."
    exit 0
  fi
  sleep 5
done

echo "::error title=Container readiness failed::$PLATFORM image did not become ready."
docker logs "$container_name" >&2 || true
exit 1
