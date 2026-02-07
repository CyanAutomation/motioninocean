---
name: pi-camera-troubleshooting
description: Diagnose motion-in-ocean camera startup and stream failures on Raspberry Pi and non-Pi environments, using runtime config, device mapping checks, health/readiness probes, and mock camera fallback.
---

## Scope and trigger conditions

Use this skill when:

- The container starts but camera streaming fails.
- `/stream.mjpg`, `/health`, or `/ready` return unexpected responses.
- Device mapping or host camera detection is uncertain.
- You are developing on non-Pi hardware and need expected mock-mode behavior.

## Fast triage inputs

Collect these before branching deeper:

```bash
docker compose ps
docker compose logs --tail=200 motion-in-ocean
curl -sS -i http://localhost:8000/health
curl -sS -i http://localhost:8000/ready
curl -sS -i http://localhost:8000/stream.mjpg
```

Good signals:
- Container is `Up` and health status is healthy.
- `/health` returns HTTP `200` with `{"status":"healthy", ...}`.
- `/ready` returns HTTP `200` with `"status":"ready"`.
- `/stream.mjpg` returns HTTP `200` and `Content-Type: multipart/x-mixed-replace`.

Bad signals:
- Container restarting/crashed.
- `/health` non-200 or timeout.
- `/ready` HTTP `503` with reasons like camera not initialized, no frames, or stale stream.
- `/stream.mjpg` HTTP `503` (`Camera stream not ready.`) or `429` (connection limit reached).

## Runtime configuration checklist (README-backed)

Validate runtime env configuration first:

```bash
docker compose config
```

Focus on these variables:

- `MOTION_IN_OCEAN_RESOLUTION` (e.g. `640x480`)
- `MOTION_IN_OCEAN_FPS`
- `MOTION_IN_OCEAN_TARGET_FPS`
- `MOTION_IN_OCEAN_JPEG_QUALITY`
- `MOTION_IN_OCEAN_MAX_STREAM_CONNECTIONS`
- `MOTION_IN_OCEAN_PI3_PROFILE`
- `MOTION_IN_OCEAN_HEALTHCHECK_READY`
- `MOCK_CAMERA`

Expected behavior:
- Healthcheck defaults to `/health`.
- If `MOTION_IN_OCEAN_HEALTHCHECK_READY=true`, healthcheck uses readiness semantics (`/ready`).
- If `MOCK_CAMERA=true`, Picamera2 init is skipped and dummy frames are produced (useful off-Pi).

## Device mapping verification (compose + detect-devices)

### Host checks

```bash
./detect-devices.sh
```

Good signals:
- Required core devices exist (`/dev/dma_heap/*`, `/dev/vchiq`).
- At least one `/dev/media*` and `/dev/video*` is detected.
- `rpicam-hello --list-cameras` succeeds.

Bad signals:
- Missing `/dev/media*` or `/dev/video*`.
- Missing `/dev/vchiq` or `/dev/dma_heap/*`.
- Camera list command fails.

### Compose checks

```bash
sed -n '/devices:/,/group_add:/p' docker-compose.yaml
```

Good signals:
- `devices:` includes host paths for dma heap, vchiq, media, and video nodes that actually exist on host.
- `/run/udev:/run/udev:ro` is mounted.
- `group_add: [video]` (or equivalent) is present.

Bad signals:
- Stale/static device entries that do not exist on current host.
- Missing udev mount.
- Missing video group access.

## Health/readiness diagnostics

### Endpoint semantics

- `/health`: liveness only; should be `200` when Flask service is running.
- `/ready`: readiness; returns `200` only when recording started and frame age is fresh.
- `/stream.mjpg`: returns `503` when recording has not started; `429` when max stream clients is exceeded.

### Commands

```bash
curl -sS -i http://localhost:8000/health
curl -sS -i http://localhost:8000/ready
curl -sS http://localhost:8000/ready | jq .
docker exec motion-in-ocean python3 /app/healthcheck.py; echo $?
```

Good signals:
- `/health` => `200`.
- `/ready` => `200` and includes readiness payload with recent `last_frame_age_seconds`.
- `healthcheck.py` exits `0`.

Bad signals:
- `/ready` => `503` + reason:
  - `Camera not initialized or recording not started`
  - `No frames captured yet`
  - `stale_stream`
- `healthcheck.py` exits non-zero.

If using readiness-based healthcheck:

```bash
docker exec motion-in-ocean env | grep -E 'HEALTHCHECK|MOTION_IN_OCEAN_HEALTHCHECK_READY'
```

Good: `MOTION_IN_OCEAN_HEALTHCHECK_READY=true` (or `HEALTHCHECK_READY=true`) matches expected policy.

## Decision tree

1. **Camera not detected**
   - Run `./detect-devices.sh`.
   - If `/dev/media*` or `/dev/video*` missing:
     - Enable camera in `raspi-config`, reboot, verify hardware seating/cable, retest with `rpicam-hello --list-cameras`.
   - If host sees camera but container does not:
     - Update `docker-compose.yaml` `devices:` mappings to match detected nodes; keep `/run/udev` mount.

2. **Stream endpoint unavailable (`/stream.mjpg`)**
   - Check `/health` then `/ready`.
   - If `/health=200` and `/ready=503`:
     - Camera pipeline not ready; inspect logs for camera init/frame capture errors.
   - If `/stream.mjpg=429`:
     - Increase `MOTION_IN_OCEAN_MAX_STREAM_CONNECTIONS` or close existing clients.
   - If `/stream.mjpg=503`:
     - Readiness not achieved yet; resolve underlying camera startup/frame freshness issue.

3. **Health endpoint unhealthy**
   - If `/health` fails: service process issue (startup crash/bind failure).
   - Run `docker compose logs --tail=200 motion-in-ocean` and restart:
     ```bash
     docker compose restart motion-in-ocean
     ```
   - Validate container healthcheck mode:
     - Default should target `/health`.
     - If readiness mode enabled, temporary camera issues may mark container unhealthy by design.

4. **Non-Pi development environment**
   - Set mock mode:
     ```bash
     export MOCK_CAMERA=true
     docker compose up -d --force-recreate
     ```
   - Expected in mock mode:
     - `/health` returns `200`.
     - `/ready` should become `200` once mock frame generator starts.
     - `/stream.mjpg` should stream dummy frames.
   - If `MOCK_CAMERA=false` on non-Pi hosts, camera initialization failures are expected.

## Diagnostic bundle to attach in issues

```bash
uname -a
cat /etc/os-release
docker compose ps
docker compose logs --tail=300 motion-in-ocean
curl -sS -i http://localhost:8000/health
curl -sS -i http://localhost:8000/ready
```

On Raspberry Pi hosts also include:

```bash
./detect-devices.sh
rpicam-hello --list-cameras
```

Include compose snippets for `devices:`, `volumes:`, and relevant environment variables (`MOTION_IN_OCEAN_*`, `MOCK_CAMERA`).
