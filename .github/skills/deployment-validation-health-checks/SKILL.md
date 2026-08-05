---
name: deployment-validation-health-checks
description: Validate post-deployment container health, verify device mapping, check health/readiness endpoints, and troubleshoot container startup issues for motion-in-ocean deployments.
owner: motion-in-ocean team
last-reviewed: 2026-08-05
category: Deployment
compatible-repo-areas:
  - containers/
  - scripts/healthcheck.py
  - Dockerfile
  - docs/guides/DEPLOYMENT.md
  - docker-compose*.yml files
  - .github/workflows/docker-publish.yml
---

## Purpose

Enable operators and developers to validate that motion-in-ocean containers start correctly, health checks pass, device mapping is correct, and streaming endpoints are available. This skill ensures deployed instances are in a healthy state and can be quickly diagnosed if they fail to start or stream.

## Scope and trigger conditions

Apply this skill when:

- After starting a new motion-in-ocean container or cluster
- Debugging container startup failures
- Verifying device mapping for Raspberry Pi camera hardware
- Testing multi-node deployments (webcam nodes + management hub)
- Troubleshooting stream unavailability or degraded health
- Validating Docker Compose configurations before production deployment
- Checking container health after configuration changes

Do NOT use this skill for:

- Fixing application code issues (use contributor-workflow or pi-camera-troubleshooting)
- Debugging network infrastructure (use network troubleshooting tools)
- Modifying container configuration or environment variables (that's deployment setup, not validation)
- Stress testing or performance benchmarking

## Required inputs

- Access to running motion-in-ocean container(s) or Docker Compose cluster
- `docker` or `docker compose` CLI available
- `curl` or `wget` to test HTTP endpoints
- Optional: `jq` for parsing JSON responses
- Container logs accessible via `docker compose logs` or `docker logs`

## Step-by-step workflow

## Related Skills

- **Container startup issues:** [`docker-debugging`](../docker-debugging/SKILL.md) (coming soon) — Debug before running health checks
- **Camera not streaming:** [`pi-camera-troubleshooting`](../pi-camera-troubleshooting/SKILL.md) — Diagnose Picamera2-specific issues
- **Feature flags:** [`feature-flag-management`](../feature-flag-management/SKILL.md) — Enable mock camera for non-Pi testing

---

### Quick health assessment

1. **Check container status:**
   ```bash
   docker compose ps
   # OR for single container
   docker ps | grep motion-in-ocean
   ```

2. **Expected output:**
   - Status shows `Up` (not `Exited`, `Dead`, or `Restarting`)
   - If health check is configured, status shows `healthy` or `starting`

3. **Check container logs for startup errors:**
   ```bash
   docker compose logs --tail=50 motion-in-ocean
   # OR for single container
   docker logs <container-id> | tail -50
   ```

4. **Expected output:**
   - No `ERROR` or `CRITICAL` messages
   - Flask app should report "Running on" with address and port
   - Camera initialization messages (if using real camera)
   - "Mock camera mode enabled" (if using `MOCK_CAMERA=true`)

### Verify health endpoint

1. **Query the health endpoint:**
   ```bash
   curl -v http://localhost:8000/health
   ```

2. **Expected response (HTTP 200):**
   ```json
   {
     "status": "healthy",
     "mode": "webcam",
     "timestamp": "2026-08-05T10:30:00Z"
   }
   ```

3. **Interpret status values:**
   - `healthy` — Container is fully operational
   - `degraded` — Container is running but some features are limited
   - `unhealthy` — Container is not functioning correctly

4. **If health is degraded or unhealthy:**
   - Check logs for warnings: `docker compose logs --tail=100 motion-in-ocean | grep -i "warn\|error"`
   - Verify required environment variables are set
   - Check device mapping (if using Pi camera)

### Verify readiness endpoint

1. **Query the readiness endpoint:**
   ```bash
   curl -v http://localhost:8000/ready
   ```

2. **Expected response (HTTP 200):**
   ```json
   {
     "status": "ready",
     "camera_initialized": true,
     "stream_available": true
   }
   ```

3. **Interpret readiness status:**
   - `ready` — Camera is initialized and streaming is available
   - `waiting` — Container is starting up, camera not yet initialized (HTTP 503)
   - `degraded` — Camera initialized but stream has issues (HTTP 200 with warnings)

4. **If not ready (HTTP 503):**
   - Container is still initializing
   - Wait 10-30 seconds and retry
   - If still not ready after 60 seconds, check logs for camera initialization errors

### Verify stream endpoint availability

1. **Test MJPEG stream:**
   ```bash
   # In webcam mode, test streaming
   curl -v http://localhost:8000/stream 2>&1 | head -20
   ```

2. **Expected response (HTTP 200):**
   - First line: `HTTP/1.1 200 OK`
   - Headers include: `Content-Type: multipart/x-mixed-replace; boundary=...`
   - Followed by JPEG frame data

3. **If stream fails (HTTP 404, 503, or connection refused):**
   - Verify container is in webcam mode (check `APP_MODE` environment variable)
   - Check camera initialization in logs
   - Verify `MOCK_CAMERA=true` if no hardware camera is available

### Verify device mapping (Raspberry Pi camera)

1. **Check device mapping in running container:**
   ```bash
   docker exec <container-id> ls -la /dev/video* /dev/mem
   ```

2. **Expected output (with real Pi camera):**
   ```
   /dev/video0 (or /dev/video10 on newer Pi OS)
   /dev/mem
   ```

3. **If devices not found:**
   - Verify Docker Compose volume mounts include camera device
   - Typical Docker Compose config:
     ```yaml
     devices:
       - /dev/video10:/dev/video10  # Raspberry Pi CSI camera
       - /dev/mem:/dev/mem          # Memory access for camera control
     ```
   - Restart container with correct device mapping

4. **Verify Picamera2 can detect camera:**
   ```bash
   docker exec <container-id> python3 -c "from picamera2 import Picamera2; cam = Picamera2(); print('Camera detected')"
   ```

5. **Expected output:** `Camera detected` (or no errors)

### Verify API endpoints and authentication

1. **Test authenticated API endpoint (if token is required):**
   ```bash
   # Without token (should fail with 401)
   curl -v http://localhost:8000/api/status
   
   # With token
   curl -v -H "Authorization: Bearer <YOUR_TOKEN>" http://localhost:8000/api/status
   ```

2. **Expected response (HTTP 200 with token):**
   ```json
   {
     "status": "ok",
     "stream_available": true,
     "fps": 24,
     "resolution": "640x480",
     "jpeg_quality": 90
   }
   ```

3. **If authentication fails:**
   - Verify `WEBCAM_CONTROL_PLANE_AUTH_TOKEN` environment variable is set
   - Ensure token format is correct (bearer token)
   - Check token matches between sender and receiver

### Verify management hub (if in management mode)

1. **Check management hub status:**
   ```bash
   curl -v http://localhost:8001/health
   ```

2. **Expected response (HTTP 200):**
   ```json
   {
     "status": "healthy",
     "mode": "management",
     "registered_nodes": 0
   }
   ```

3. **Test node registry endpoint:**
   ```bash
   curl -v -H "Authorization: Bearer <MANAGEMENT_TOKEN>" http://localhost:8001/api/nodes
   ```

4. **Expected response (HTTP 200):**
   ```json
   {
     "nodes": [],
     "total": 0
   }
   ```

### Comprehensive health check script

1. **Run automated health check:**
   ```bash
   python3 scripts/healthcheck.py
   ```

2. **Expected output:** Detailed status report with all checks passing

3. **If any check fails:**
   - Script will indicate which check failed
   - Review logs and previous steps for remediation

### Validate multi-host deployment

1. **Check webcam node registration with management hub:**
   - Management hub should discover and list webcam nodes
   - Each node should announce periodically (default: every 60 seconds)

2. **Verify node health from hub perspective:**
   ```bash
   curl -v -H "Authorization: Bearer <MANAGEMENT_TOKEN>" http://localhost:8001/api/nodes/<node-id>
   ```

3. **Expected response (HTTP 200):**
   - Node status, last seen timestamp, address, port
   - Last health check result

4. **If nodes not appearing in hub:**
   - Verify webcam nodes have `DISCOVERY_ENABLED=true`
   - Check `DISCOVERY_MANAGEMENT_URL` points to hub
   - Verify `DISCOVERY_TOKEN` matches hub's `NODE_DISCOVERY_SHARED_SECRET`
   - Check network connectivity between nodes and hub
   - Review webcam node logs for discovery errors

## Validation checklist

- [ ] Container status is `Up` (not `Exited` or `Restarting`)
- [ ] Container has `healthy` status (if health check configured)
- [ ] `/health` endpoint returns HTTP 200 with `status: healthy`
- [ ] `/ready` endpoint returns HTTP 200 (ready) or HTTP 503 (waiting during startup)
- [ ] `/stream` endpoint returns HTTP 200 with MJPEG stream (webcam mode only)
- [ ] `/api/status` endpoint requires and accepts bearer token authentication
- [ ] Device `/dev/video*` is mapped in container (if using real Pi camera)
- [ ] Camera is detected and initialized (check logs)
- [ ] Multi-node setup: nodes are discovered and listed in management hub
- [ ] No errors or critical warnings in container logs

## Source of truth

- `docs/guides/DEPLOYMENT.md` — Complete deployment guide including multi-host setup
- `containers/README.md` — Docker Compose configuration and orchestration guidance
- `scripts/healthcheck.py` — Automated health check script implementation
- `Dockerfile` — Container configuration, health check definition, entrypoint
- `pi_camera_in_docker/shared.py` — Health/ready endpoint implementation
- `.github/workflows/docker-publish.yml` — Release and image build behavior

## Common failure modes and recovery actions

| Failure | Cause | Recovery |
|---------|-------|----------|
| Container in `Exited` state | Startup error, missing env var, or crash | Check logs: `docker compose logs motion-in-ocean`; review error messages; verify environment variables |
| `/health` returns HTTP 503 or error | Application startup in progress or critical error | Wait 30 seconds and retry; check logs for `ERROR` messages |
| `/ready` returns HTTP 503 (waiting) longer than 60s | Camera initialization timeout or hardware issue | Check camera device is present: `ls -la /dev/video*`; verify device mapping in docker-compose.yml |
| `/stream` returns HTTP 404 | Container is in management mode, not webcam mode | Verify `APP_MODE=webcam` environment variable; check deployment type |
| Authentication fails (HTTP 401) | Missing or incorrect bearer token | Verify token format: `Authorization: Bearer <token>`; check token matches env var; base64 decode if needed |
| Device not found (no `/dev/video*`) | Device not mounted in container | Update docker-compose.yml with correct device mapping; restart container |
| Camera detection fails | Camera not connected, disabled, or firmware issue (Pi-specific) | Check Pi camera is enabled in raspi-config; verify CSI ribbon cable is connected; try mock mode |
| Multi-host: nodes not appearing in hub | Discovery disabled, network issue, or token mismatch | Verify `DISCOVERY_ENABLED=true` on webcam nodes; check network connectivity; verify tokens match |
| Stream very slow or choppy | Network bandwidth limited, CPU throttled, or fps/resolution too high | Check network bandwidth; reduce resolution or fps; monitor CPU usage; check for thermal throttling |

## Maintenance notes

- Review and refresh this skill **when deployment infrastructure or health check implementation changes**
- Update `last-reviewed` when changes are made to:
  - Health check endpoints (`pi_camera_in_docker/shared.py`)
  - Dockerfile or health check definition
  - Deployment guides or Docker Compose configs
  - Device mapping or environment variable requirements
  - Multi-host discovery behavior

- Regular monitoring tasks:
  - Quarterly: Review health check success rates across deployments
  - As-needed: Test deployment after major code changes
  - Before releases: Validate all health checks pass on release candidate

## Writing standards

- Use imperative voice in workflow steps (e.g., "Check container status" not "Checking...")
- Include exact command-line examples with realistic output
- Explain both successful cases and failure scenarios
- Keep validation checklist tied to observable health check outputs
- Document multi-host setup clearly as it's complex
