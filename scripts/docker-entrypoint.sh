#!/bin/sh
set -eu

APP_UID="${APP_UID:-10001}"
APP_GID="${APP_GID:-10001}"
DATA_DIR="${DATA_DIR:-/data}"
export DATA_DIR

# Suppress libcamera C++ INFO/DEBUG lines which use a different timestamp format and
# clutter docker logs. Override with: LIBCAMERA_LOG_LEVELS=*:DEBUG docker compose up
export LIBCAMERA_LOG_LEVELS="${LIBCAMERA_LOG_LEVELS:-*:WARNING}"

CAMERA_CLI_MISSING_ERROR="Neither rpicam-hello nor libcamera-hello is available in PATH."

# UTC ISO-8601 timestamp helper for structured log line prefixes.
ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

detect_camera_cli() {
    if command -v rpicam-hello >/dev/null 2>&1; then
        echo "rpicam-hello"
        return 0
    fi
    if command -v libcamera-hello >/dev/null 2>&1; then
        echo "libcamera-hello"
        return 0
    fi
    return 1
}


# Dump image provenance info for debugging and validation
dump_provenance() {
    echo "[entrypoint] === Image Provenance ===" >&2
    
    if [ -f /app/BUILD_METADATA ]; then
        echo "[entrypoint] BUILD_METADATA:" >&2
        cat /app/BUILD_METADATA | sed 's/^/[entrypoint]   /' >&2
    else
        echo "[entrypoint] BUILD_METADATA: not found" >&2
    fi
    
    echo "[entrypoint] libcamera version:" >&2
    if CAMERA_CLI="$(detect_camera_cli)"; then
        echo "[entrypoint]   camera_cli=${CAMERA_CLI}" >&2
        "${CAMERA_CLI}" --version 2>&1 | sed 's/^/[entrypoint]   /' >&2 || true
    else
        echo "[entrypoint] WARNING: ${CAMERA_CLI_MISSING_ERROR}" >&2
    fi
    
    echo "[entrypoint] picamera2 import path:" >&2
    if command -v python3 >/dev/null 2>&1; then
        python3 -c "import picamera2; print(picamera2.__file__)" 2>&1 | sed 's/^/[entrypoint]   /' >&2 || echo "[entrypoint]   import failed" >&2
    else
        echo "[entrypoint]   python3 not found" >&2
    fi
    
    echo "[entrypoint] Camera packages (dpkg):" >&2
    if command -v dpkg >/dev/null 2>&1; then
        dpkg -l | grep -E 'libcamera|picamera2|rpicam' 2>&1 | sed 's/^/[entrypoint]   /' >&2 || echo "[entrypoint]   no camera packages found" >&2
    else
        echo "[entrypoint]   dpkg not found" >&2
    fi
    
    if [ -f /etc/apt/preferences.d/rpi-camera.preferences ]; then
        echo "[entrypoint] Apt pinning (/etc/apt/preferences.d/rpi-camera.preferences):" >&2
        cat /etc/apt/preferences.d/rpi-camera.preferences | sed 's/^/[entrypoint]   /' >&2
    fi
    
    echo "[entrypoint] === End Provenance ===" >&2
}

log_writable_status() {
    if [ -w "${DATA_DIR}" ]; then
        echo "[entrypoint] $(ts) INFO ${DATA_DIR} writable=yes checked_as_uid=$(id -u)"
    else
        echo "[entrypoint] $(ts) ERROR ${DATA_DIR} writable=no checked_as_uid=$(id -u)" >&2
    fi
}

if [ "$(id -u)" -eq 0 ]; then
    dump_provenance
    
    mkdir -p "${DATA_DIR}"
    if chown -Rh "${APP_UID}:${APP_GID}" "${DATA_DIR}"; then
        echo "[entrypoint] $(ts) INFO Updated ownership for ${DATA_DIR} to ${APP_UID}:${APP_GID}"
    else
        echo "[entrypoint] $(ts) ERROR Failed to update ownership for ${DATA_DIR} to ${APP_UID}:${APP_GID}" >&2
    fi

    gosu app sh -c 'ts(){ date -u +"%Y-%m-%dT%H:%M:%SZ"; }; log_writable_status(){ if [ -w "$DATA_DIR" ]; then echo "[entrypoint] $(ts) INFO $DATA_DIR writable=yes checked_as_uid=$(id -u)"; else echo "[entrypoint] $(ts) ERROR $DATA_DIR writable=no checked_as_uid=$(id -u)" >&2; fi; }; log_writable_status'

    exec gosu app "$@"
fi

log_writable_status
exec "$@"
