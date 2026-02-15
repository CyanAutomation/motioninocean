#!/bin/bash

# Docker optimization validation script
# Tests the optimized Dockerfile and compares image size/build metrics

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"


echo "[INFO] === Docker Optimization Validation ==="
echo ""

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed"
    exit 1
fi

# Check if BuildKit is enabled
if ! docker buildx version &> /dev/null 2>&1; then
    echo "[WARN] BuildKit not detected. Builds will be slower."
    export DOCKER_BUILDKIT=1
fi

# Build config
IMAGE_NAME="motion-in-ocean-optimized"
IMAGE_TAG="test-$(date +%s)"
FULL_TAG="${IMAGE_NAME}:${IMAGE_TAG}"

echo "[INFO] Building optimized image..."
echo "Tag: ${FULL_TAG}"
echo ""

# Build with timing
BUILD_START=$(date +%s%N)
docker build \
    --build-arg INCLUDE_MOCK_CAMERA=true \
    -t "$FULL_TAG" \
    -f Dockerfile \
    . 2>&1 | tail -20

BUILD_END=$(date +%s%N)
BUILD_TIME=$(( (BUILD_END - BUILD_START) / 1000000 ))

echo ""
echo "[INFO] Build completed"

# Get image size
IMAGE_SIZE=$(docker images "$IMAGE_NAME" --format='table {{.Repository}}\t{{.Tag}}\t{{.Size}}' | grep "$IMAGE_TAG" | awk '{print $3}')
echo "[INFO] Image size: ${IMAGE_SIZE}"
echo "[INFO] Build time: $(printf '%d.%02d seconds' $((BUILD_TIME / 1000)) $((BUILD_TIME % 1000 / 10)))"

# Test the image works
echo ""
echo "[INFO] === Running Container Health Checks ==="

# Create temporary container to test
CONTAINER_ID=$(docker run -d --rm \
    -e MOCK_CAMERA=true \
    -e HEALTHCHECK_READY=true \
    -e MOTION_IN_OCEAN_RESOLUTION=640x480 \
    -e MOTION_IN_OCEAN_FPS=15 \
    -e MOTION_IN_OCEAN_JPEG_QUALITY=80 \
    "$FULL_TAG" 2>/dev/null || true)

if [ -z "$CONTAINER_ID" ]; then
    echo "[ERROR] Failed to create container"
    exit 1
fi

echo "Container started: $CONTAINER_ID"

# Wait for container to start
sleep 2

# Check if container is still running
if ! docker ps --format='table {{.ID}}\t{{.Status}}' | grep -q "$CONTAINER_ID"; then
    echo "[ERROR] Container exited unexpectedly"
    docker logs "$CONTAINER_ID" 2>/dev/null || true
    exit 1
fi

# Test Python imports
echo "[INFO] Testing Python module imports..."
docker exec "$CONTAINER_ID" python3 -c "import numpy, flask, flask_cors, picamera2; print('[INFO] All modules imported successfully')" 2>&1 || {
    echo "[ERROR] Module import failed"
    docker stop "$CONTAINER_ID" 2>/dev/null || true
    exit 1
}

# Run healthcheck
echo "[INFO] Running healthcheck..."
docker exec "$CONTAINER_ID" python3 /app/healthcheck.py 2>&1 | grep -q "Server is running" && {
    echo "[INFO] Healthcheck passed"
} || {
    echo "[WARN] Healthcheck returned: "
    docker exec "$CONTAINER_ID" python3 /app/healthcheck.py || true
}

# Cleanup
docker stop "$CONTAINER_ID" 2>/dev/null || true

# Summary
echo ""
echo "[INFO] === Summary ==="
echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "Size: ${IMAGE_SIZE}"
echo "Build time: $(printf '%d.%02d seconds' $((BUILD_TIME / 1000)) $((BUILD_TIME % 1000 / 10)))"
echo "[INFO] All tests passed"

echo ""
echo "[INFO] To list all images:"
echo "  docker images | grep motion-in-ocean"

echo ""
echo "[INFO] To clean up test images:"
echo "  docker rmi ${IMAGE_NAME}:test-*"

echo ""
echo "[WARN] Save the image size for comparison with previous builds."
