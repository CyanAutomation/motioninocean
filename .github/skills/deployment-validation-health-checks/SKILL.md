---
name: deployment-validation-health-checks
description: Verify a running webcam or management deployment, including container health, readiness, API access, and camera-device mapping.
owner: motion-in-ocean team
last-reviewed: 2026-09-25
category: Deployment
compatible-repo-areas:
  - containers/
  - scripts/healthcheck.py
  - Dockerfile
  - docs/guides/DEPLOYMENT.md
---

## Purpose

Confirm that the selected Compose deployment is running and its health, readiness, and expected service endpoints behave correctly.

## Scope and trigger conditions

- Use after deploying or changing a webcam node or management hub.
- Use [`pi-camera-troubleshooting`](../pi-camera-troubleshooting/SKILL.md) when webcam readiness or camera initialization fails.
- Use `docs/guides/DEPLOYMENT.md` for deployment configuration and authentication details.

## Required inputs

- Deployment mode and Compose directory.
- Host access to Docker and the configured host port.
- Bearer token when an endpoint is protected by the deployment’s authentication settings.

## Step-by-step workflow

1. Validate the intended Compose configuration before starting it:

   ```bash
   docker compose -f containers/motion-in-ocean-webcam/docker-compose.yaml config
   ```

   For the management hub, use `containers/motion-in-ocean-management/docker-compose.yaml`.
2. Check service state and recent logs with `docker compose ps` and `docker compose logs --tail=100` from the selected deployment directory.
3. Check the published port from the host. Webcam defaults to port 8000; management defaults to port 8001. Both modes serve the application on container port 8000.
4. Check `GET /health`. It is a liveness endpoint and returns HTTP 200 with `status: "ok"` when the app responds.
5. Check `GET /ready`. A webcam returns 200 with `status: "ready"` after capture starts and frames are fresh; before then it returns 503 with `status: "not_ready"`. Management mode returns ready without camera initialization.
6. In webcam mode, check `GET /stream.mjpg` for an MJPEG response. Check `/api/status` with the configured bearer token when authentication is enabled.
7. If the camera is unavailable, compare mapped devices with host devices. For production, prefer `docker-compose.hardened.yaml`, which disables privileged mode and maps explicit devices; the default webcam Compose file uses `privileged: true`.
8. Record mode, Compose file, image tag, endpoint results, and any device/auth limitations.

## Validation checklist

- [ ] Compose config renders without errors.
- [ ] Expected container is running and not restarting.
- [ ] `/health` returns 200 with `status: "ok"`.
- [ ] `/ready` matches the selected mode and startup state.
- [ ] Webcam `/stream.mjpg` responds with the expected MJPEG content type.
- [ ] Protected endpoints are checked with the intended bearer token.
- [ ] Camera deployments expose only the device access required by their security posture.

## Source of truth

- `containers/motion-in-ocean-webcam/docker-compose.yaml` — Webcam port, environment, health check, and default device access.
- `containers/motion-in-ocean-webcam/docker-compose.hardened.yaml` — Explicit device access without privileged mode.
- `containers/motion-in-ocean-management/docker-compose.yaml` — Management mode and host port.
- `pi_camera_in_docker/shared.py` — `/health` and `/ready` response contracts.
- `pi_camera_in_docker/modes/webcam.py` — `/stream.mjpg` route.
- `docs/guides/DEPLOYMENT.md` — Deployment, token, and mode details.

## Common failure modes and recovery actions

- **Failure:** `/health` fails or times out. **Recovery:** Inspect container state and startup logs before checking mode-specific routes.
- **Failure:** `/ready` stays not ready. **Recovery:** Check camera initialization, frame freshness, and device mappings; follow [`pi-camera-troubleshooting`](../pi-camera-troubleshooting/SKILL.md).
- **Failure:** `/stream.mjpg` returns 404. **Recovery:** Confirm webcam mode and the host port mapping.
- **Failure:** An API request returns 401/403. **Recovery:** Confirm the correct token for that mode and endpoint; do not put tokens in logs or reports.
- **Failure:** The camera works only with privileged mode. **Recovery:** Inspect explicit device and group mappings in the hardened Compose file and validate on the target Raspberry Pi.

## Related Skills

- [`pi-camera-troubleshooting`](../pi-camera-troubleshooting/SKILL.md) — Diagnose camera and stream startup.
- [`feature-flag-management`](../feature-flag-management/SKILL.md) — Configure mock camera mode.
- [`contributor-workflow`](../contributor-workflow/SKILL.md) — Implement a deployment fix.

## Maintenance notes

Review this skill when Compose files, routes, port mappings, health checks, or authentication boundaries change.
