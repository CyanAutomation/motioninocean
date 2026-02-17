#!/bin/sh
set -eu

APP_UID="${APP_UID:-10001}"
APP_GID="${APP_GID:-10001}"
DATA_DIR="${DATA_DIR:-/data}"
export DATA_DIR

log_writable_status() {
    if [ -w "${DATA_DIR}" ]; then
        echo "[entrypoint] ${DATA_DIR} writable=yes checked_as_uid=$(id -u)"
    else
        echo "[entrypoint] ${DATA_DIR} writable=no checked_as_uid=$(id -u)" >&2
    fi
}

if [ "$(id -u)" -eq 0 ]; then
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
