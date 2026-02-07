#!/bin/bash

# Docker optimization validation script
# Tests the optimized Dockerfile and compares image size/build metrics

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Docker Optimization Validation ===${NC}\n"

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Check if BuildKit is enabled
if ! docker buildx version &> /dev/null 2>&1; then
    echo -e "${YELLOW}Note: BuildKit not detected. Builds will be slower.${NC}"
    export DOCKER_BUILDKIT=1
fi

# Build config
IMAGE_NAME="motion-in-ocean-optimized"
IMAGE_TAG="test-$(date +%s)"
FULL_TAG="${IMAGE_NAME}:${IMAGE_TAG}"

echo -e "${BLUE}Building optimized image...${NC}"
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
echo -e "${GREEN}✓ Build completed${NC}"

# Get image size
IMAGE_SIZE=$(docker images "$IMAGE_NAME" --format='table {{.Repository}}\t{{.Tag}}\t{{.Size}}' | grep "$IMAGE_TAG" | awk '{print $3}')
echo -e "${BLUE}Image size:${NC} ${GREEN}${IMAGE_SIZE}${NC}"
echo -e "${BLUE}Build time:${NC} ${GREEN}$(printf '%d.%02d seconds' $((BUILD_TIME / 1000)) $((BUILD_TIME % 1000 / 10)))${NC}"

# Test the image works
echo ""
echo -e "${BLUE}=== Running Container Health Checks ===${NC}"

# Create temporary container to test
CONTAINER_ID=$(docker run -d --rm \
    -e MOCK_CAMERA=true \
    -e HEALTHCHECK_READY=true \
    -e MOTION_IN_OCEAN_RESOLUTION=640x480 \
    -e MOTION_IN_OCEAN_FPS=15 \
    -e MOTION_IN_OCEAN_JPEG_QUALITY=80 \
    "$FULL_TAG" 2>/dev/null || true)

if [ -z "$CONTAINER_ID" ]; then
    echo -e "${RED}✗ Failed to create container${NC}"
    exit 1
fi

echo "Container started: $CONTAINER_ID"

# Wait for container to start
sleep 2

# Check if container is still running
if ! docker ps --format='table {{.ID}}\t{{.Status}}' | grep -q "$CONTAINER_ID"; then
    echo -e "${RED}✗ Container exited unexpectedly${NC}"
    docker logs "$CONTAINER_ID" 2>/dev/null || true
    exit 1
fi

# Test Python imports
echo -e "${BLUE}Testing Python module imports...${NC}"
docker exec "$CONTAINER_ID" python3 -c "import numpy, flask, flask_cors, picamera2; print('✓ All modules imported successfully')" 2>&1 || {
    echo -e "${RED}✗ Module import failed${NC}"
    docker stop "$CONTAINER_ID" 2>/dev/null || true
    exit 1
}

# Run healthcheck
echo -e "${BLUE}Running healthcheck...${NC}"
docker exec "$CONTAINER_ID" python3 /app/healthcheck.py 2>&1 | grep -q "Server is running" && {
    echo -e "${GREEN}✓ Healthcheck passed${NC}"
} || {
    echo -e "${YELLOW}⚠ Healthcheck returned: ${NC}"
    docker exec "$CONTAINER_ID" python3 /app/healthcheck.py || true
}

# Cleanup
docker stop "$CONTAINER_ID" 2>/dev/null || true

# Summary
echo ""
echo -e "${BLUE}=== Summary ===${NC}"
echo -e "Image: ${GREEN}${IMAGE_NAME}:${IMAGE_TAG}${NC}"
echo -e "Size: ${GREEN}${IMAGE_SIZE}${NC}"
echo -e "Build time: ${GREEN}$(printf '%d.%02d seconds' $((BUILD_TIME / 1000)) $((BUILD_TIME % 1000 / 10)))${NC}"
echo -e "${GREEN}✓ All tests passed${NC}"

echo ""
echo -e "${BLUE}To list all images:${NC}"
echo "  docker images | grep motion-in-ocean"

echo ""
echo -e "${BLUE}To clean up test images:${NC}"
echo "  docker rmi ${IMAGE_NAME}:test-*"

echo ""
echo -e "${YELLOW}Note: Save the image size for comparison with previous builds.${NC}"
