#!/bin/bash
# validate-deployment.sh - Test motion-in-ocean deployment on Raspberry Pi
# This script validates that the container is running correctly with camera access

set -e

CONTAINER_NAME="motion-in-ocean"
PORT="${MOTION_IN_OCEAN_WEBCAM_PORT:-8000}"
MAX_WAIT=60

echo "[INFO] motion-in-ocean Deployment Validation"
echo "=========================================="
echo ""

# Check if container exists
if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "[ERROR] Container '${CONTAINER_NAME}' not found"
    echo "   Run: docker compose up -d"
    exit 1
fi

# Check container status
CONTAINER_STATUS=$(docker inspect -f '{{.State.Status}}' "${CONTAINER_NAME}")
echo "[INFO] Container Status: ${CONTAINER_STATUS}"

if [ "${CONTAINER_STATUS}" != "running" ]; then
    echo "[ERROR] Container is not running"
    echo ""
    echo "Last 20 lines of logs:"
    docker logs --tail 20 "${CONTAINER_NAME}"
    exit 1
fi

# Check health status
HEALTH_STATUS=$(docker inspect -f '{{.State.Health.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "none")
echo "[INFO] Health Status: ${HEALTH_STATUS}"

if [ "${HEALTH_STATUS}" = "starting" ]; then
    echo "[INFO] Container is starting, waiting for healthy status..."
    WAITED=0
    while [ "${HEALTH_STATUS}" = "starting" ] && [ ${WAITED} -lt ${MAX_WAIT} ]; do
        sleep 2
        WAITED=$((WAITED + 2))
        HEALTH_STATUS=$(docker inspect -f '{{.State.Health.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "none")
        echo "   Status: ${HEALTH_STATUS} (${WAITED}s elapsed)"
    done
fi

if [ "${HEALTH_STATUS}" = "unhealthy" ] || [ "${HEALTH_STATUS}" = "starting" ]; then
    echo "[ERROR] Container is unhealthy or still starting after ${MAX_WAIT}s"
    echo ""
    echo "Recent logs:"
    docker logs --tail 30 "${CONTAINER_NAME}"
    exit 1
fi

echo ""
echo "[INFO] Testing endpoints:"
echo ""

# Test health endpoint
echo "Testing /health..."
if curl -fsS "http://localhost:${PORT}/health" >/dev/null 2>&1; then
    echo "  [INFO] /health endpoint responding"
else
    echo "  [ERROR] /health endpoint not responding"
    exit 1
fi

# Test metrics endpoint
echo "Testing /metrics..."
METRICS=$(curl -fsS "http://localhost:${PORT}/metrics" 2>/dev/null || echo "")
if [ -n "${METRICS}" ]; then
    echo "  [INFO] /metrics endpoint responding"
    echo ""
    echo "[INFO] Current metrics:"
    echo "${METRICS}" | python3 -m json.tool 2>/dev/null || echo "${METRICS}"
else
    echo "  [ERROR] /metrics endpoint not responding"
    exit 1
fi

echo ""
echo "[INFO] Camera status:"
echo ""

# Parse metrics for camera status
CAMERA_ACTIVE=$(echo "${METRICS}" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('camera_active', False))" 2>/dev/null || echo "unknown")
FRAMES=$(echo "${METRICS}" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('frames_captured', 0))" 2>/dev/null || echo "0")
FPS=$(echo "${METRICS}" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('current_fps', 0))" 2>/dev/null || echo "0")

echo "  Camera Active: ${CAMERA_ACTIVE}"
echo "  Frames Captured: ${FRAMES}"
echo "  Current FPS: ${FPS}"

if [ "${CAMERA_ACTIVE}" != "True" ] && [ "${CAMERA_ACTIVE}" != "true" ]; then
    echo ""
    echo "[WARN] Camera not active - check logs for errors"
    echo ""
    echo "Recent logs:"
    docker logs --tail 20 "${CONTAINER_NAME}"
    exit 1
fi

echo ""
echo "[INFO] Resource usage:"
echo ""
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" "${CONTAINER_NAME}"

echo ""
echo "[INFO] System temperature:"
if command -v vcgencmd &> /dev/null; then
    vcgencmd measure_temp
else
    echo "  (vcgencmd not available)"
fi

echo ""
echo "[INFO] Validation complete."
echo ""
echo "[INFO] Access the camera stream:"
echo "   Local: http://localhost:${PORT}/"
echo "   Network: http://$(hostname -I | awk '{print $1}'):${PORT}/"
echo ""
echo "[INFO] View metrics:"
echo "   curl http://localhost:${PORT}/metrics"
echo ""
echo "[INFO] Monitor logs:"
echo "   docker compose logs -f ${CONTAINER_NAME}"
