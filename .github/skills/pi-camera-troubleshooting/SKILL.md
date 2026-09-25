---
name: pi-camera-troubleshooting
description: Diagnose Raspberry Pi camera initialization, missing device mappings, and unavailable webcam streams. Use when a webcam deployment is running but not ready or not capturing frames.
owner: motion-in-ocean team
last-reviewed: 2026-09-25
category: Deployment
compatible-repo-areas:
  - pi_camera_in_docker/modes/webcam.py
  - containers/motion-in-ocean-webcam/
  - scripts/detect-devices.sh
  - scripts/healthcheck.py
---

## Purpose

Find whether a webcam failure comes from application readiness, camera hardware, container device access, or deployment configuration.

## Scope and trigger conditions

- Use when a Raspberry Pi webcam container starts but the camera does not initialize or stream.
- Use [`deployment-validation-health-checks`](../deployment-validation-health-checks/SKILL.md) for general deployment checks.
- Use `MIO_MOCK_CAMERA=true` for host-side application checks that do not require CSI hardware.

## Required inputs

- Raspberry Pi model, OS/kernel, camera module, and connection details.
- Selected webcam Compose file and recent container logs.
- Host access to camera enumeration and device nodes.

## Step-by-step workflow

1. Check service state and recent logs from `containers/motion-in-ocean-webcam/`:

   ```bash
   docker compose ps
   docker compose logs --tail=200
   ```

2. Check `/health` and `/ready`. `/health` returns `status: "ok"` when the app responds. Webcam `/ready` returns `status: "ready"` with HTTP 200 after recording starts and frames are fresh; otherwise it returns HTTP 503 with `status: "not_ready"`.
3. Check the stream endpoint:

   ```bash
   curl -sS -i http://localhost:8000/stream.mjpg
   ```

   If webcam authentication is configured, add the matching bearer token to protected endpoint requests.
4. On the Raspberry Pi host, run `rpicam-hello --list-cameras` (or the camera enumeration tool installed for that OS). Confirm the CSI cable is seated and the camera appears.
5. Inspect required host devices and run `./scripts/detect-devices.sh` from the repository root. Compare detected nodes with the selected Compose file’s explicit device mappings.
6. Start with the default webcam Compose file to establish the baseline. For production, use `docker-compose.hardened.yaml` and map only the detected devices; the default file enables privileged mode.
7. If application behavior must be isolated from hardware, set `MIO_MOCK_CAMERA=true` and recreate the service. Confirm mock frames make `/ready` and `/stream.mjpg` available.
8. Capture the first camera error, device list, Compose mode, and endpoint results before changing kernel, permissions, or deployment settings.

## Validation checklist

- [ ] Camera enumerates successfully on the host.
- [ ] Required device nodes are present in the container.
- [ ] Logs show whether camera initialization completed or failed.
- [ ] `/ready` matches camera/frame state.
- [ ] `/stream.mjpg` returns an MJPEG response when ready.
- [ ] Mock mode is controlled with the canonical `MIO_MOCK_CAMERA` variable.
- [ ] Production deployment avoids unnecessary privileged access.

## Source of truth

- `pi_camera_in_docker/modes/webcam.py` — Camera startup, frame capture, readiness, and stream route.
- `pi_camera_in_docker/shared.py` — `/health`, `/ready`, and webcam token protection.
- `pi_camera_in_docker/feature_flags.py` — Mock-camera flag environment name.
- `containers/motion-in-ocean-webcam/docker-compose.yaml` — Default webcam container/device setup.
- `containers/motion-in-ocean-webcam/docker-compose.hardened.yaml` — Explicit device-access deployment.
- `scripts/detect-devices.sh` — Host device detection.
- `docs/guides/DEPLOYMENT.md` — Supported deployment and authentication guidance.

## Common failure modes and recovery actions

- **Failure:** Host camera enumeration fails. **Recovery:** Check cable orientation, camera enablement, supported OS/kernel packages, and device-specific Raspberry Pi diagnostics.
- **Failure:** Camera works on the host but not in the container. **Recovery:** Compare host device paths and permissions with Compose mappings; test the hardened file with the required groups/devices.
- **Failure:** `/ready` returns 503 while `/health` returns 200. **Recovery:** Read camera initialization logs and check whether frames are being captured and remain fresh.
- **Failure:** `/stream.mjpg` returns 404. **Recovery:** Confirm `MIO_APP_MODE=webcam` and the expected host port.
- **Failure:** Mock mode has no effect. **Recovery:** Confirm `MIO_MOCK_CAMERA` appears in the container environment and recreate the container.
- **Failure:** `/stream.mjpg` returns 429. **Recovery:** Check current stream connections and the configured connection limit.

## Related Skills

- [`deployment-validation-health-checks`](../deployment-validation-health-checks/SKILL.md) — Validate the overall deployment.
- [`feature-flag-management`](../feature-flag-management/SKILL.md) — Configure the mock-camera flag.
- [`ci-triage`](../ci-triage/SKILL.md) — Diagnose CI failures affecting camera code.

## Maintenance notes

Review this skill when camera startup, device requirements, Compose mappings, health routes, or the mock-camera flag changes.
