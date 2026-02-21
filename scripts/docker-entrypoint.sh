#!/bin/sh
set -eu

APP_UID="${APP_UID:-10001}"
APP_GID="${APP_GID:-10001}"
DATA_DIR="${DATA_DIR:-/data}"
export DATA_DIR

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
    if command -v libcamera-hello >/dev/null 2>&1; then
        libcamera-hello --version 2>&1 | sed 's/^/[entrypoint]   /' >&2 || true
    else
        echo "[entrypoint]   libcamera-hello not found" >&2
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
        echo "[entrypoint] ${DATA_DIR} writable=yes checked_as_uid=$(id -u)"
    else
        echo "[entrypoint] ${DATA_DIR} writable=no checked_as_uid=$(id -u)" >&2
    fi
}

if [ "$(id -u)" -eq 0 ]; then
    dump_provenance
    
    mkdir -p "${DATA_DIR}"
    if chown -Rh "${APP_UID}:${APP_GID}" "${DATA_DIR}"; then
        echo "[entrypoint] Updated ownership for ${DATA_DIR} to ${APP_UID}:${APP_GID}"
    else
        echo "[entrypoint] WARNING: Failed to update ownership for ${DATA_DIR} to ${APP_UID}:${APP_GID}" >&2
    fi

    gosu app sh -c 'log_writable_status(){ if [ -w "$DATA_DIR" ]; then echo "[entrypoint] $DATA_DIR writable=yes checked_as_uid=$(id -u)"; else echo "[entrypoint] $DATA_DIR writable=no checked_as_uid=$(id -u)" >&2; fi; }; log_writable_status'

    exec gosu app "$@"
fi

log_writable_status
exec "$@"
