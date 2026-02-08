# PRD (Backend): motion-in-ocean

## TL;DR

This PRD defines the backend requirements for motion-in-ocean: a Docker-first Raspberry Pi CSI camera streaming service with MJPEG output, robust health/readiness semantics, environment-driven configuration, and operability-focused deployment details. For UI behavior and stream viewing requirements, see [PRD-frontend.md](PRD-frontend.md).

---

## Problem Statement

Running a Raspberry Pi CSI camera inside Docker is non-trivial due to libcamera dependencies, device mappings, and the need for reliable health checks. Homelab users want a simple, containerized backend that streams video reliably, exposes clear health/readiness signals, and can be deployed without custom host-side software.

---

## Goals / Success Metrics

- **Reliable streaming backend:** The service consistently exposes a working MJPEG stream when the camera is available.
- **Predictable health semantics:** `/health` indicates liveness; `/ready` indicates readiness only when frames are flowing and fresh.
- **Simple deployment:** Users can deploy with a Docker image and minimal host configuration (device mappings + env file).
- **Operational clarity:** Operators can inspect status, FPS, and basic metrics via `/ready` and `/metrics`.

---

## User Stories (Backend)

- As a homelab operator, I want a Docker image that streams my Pi CSI camera so that I can view it on my network without installing host software.
- As a deployer, I want explicit health and readiness endpoints so that Docker and monitoring tools can detect failure states.
- As a developer, I want mock mode to validate the service without camera hardware.
- As an integrator, I want MJPEG output and CORS controls so that I can embed the stream in dashboards or other tools.

---

## Prioritized Functional Requirements

| Priority | Feature | Description |
| --- | --- | --- |
| P1 | MJPEG Streaming Endpoint | Provide a stable MJPEG stream at `/stream.mjpg` with appropriate headers and a 503 response if not ready. |
| P1 | Health & Readiness Probes | `/health` returns 200 if the server is running; `/ready` returns 200 only when frames are flowing and not stale, else 503 with diagnostic details. |
| P1 | Raspberry Pi CSI Camera Capture | Use Picamera2/libcamera to capture frames in a headless container, with required device mappings. |
| P1 | Environment-Driven Configuration | Support resolution, FPS, JPEG quality, CORS origins, and mock mode via environment variables. |
| P2 | Metrics Endpoint | Expose `/metrics` with uptime, frame counts, FPS, and configuration details. |
| P3 | Mock Camera Mode | Allow a mock stream for development environments without CSI hardware. |

---

## Functional Requirements

### 1. MJPEG Streaming Endpoint (P1)

**Endpoint:** `GET /stream.mjpg`

**Behavior:**

- Streams multipart MJPEG frames with `boundary=frame`.
- Returns HTTP 503 with a short message if the camera is not ready.
- Adds cache-control headers to prevent stale stream caching.

### 2. Health & Readiness Probes (P1)

**Endpoints:**

- `GET /health` → Always returns 200 with `{ status: "healthy" }` and timestamp.
- `GET /ready` → Returns 200 when the camera has started recording **and** the latest frame age is within the configured threshold; otherwise returns 503 with reason and diagnostic fields.

**Readiness details:**

- Must indicate `not_ready` status when:
  - Camera recording is not started.
  - No frames have been captured yet.
  - Latest frame age exceeds `MAX_FRAME_AGE_SECONDS`.

### 3. Raspberry Pi CSI Camera Capture (P1)

**Behavior:**

- Use Picamera2 and libcamera to capture frames in BGR format.
- Support FPS limiting when configured.
- Start recording via JPEG encoder and stream output.
- Gracefully shut down recording on exit.

### 4. Environment-Driven Configuration (P1)

**Required environment variables:**

- `RESOLUTION` (default `640x480`, max `4096x4096`)
- `FPS` (default `0` for camera default, max 120)
- `JPEG_QUALITY` (default `100`)
- `CORS_ORIGINS` (default `*` unless set)
- `MOCK_CAMERA` (default `false`)
- `MAX_FRAME_AGE_SECONDS` (default `10`)

**Validation rules:**

- Invalid or out-of-range values fall back to safe defaults.

### 5. Metrics Endpoint (P2)

**Endpoint:** `GET /metrics`

**Behavior:**

- Returns JSON with uptime, FPS, frame counts, last frame age, resolution, and timestamp.
- Intended for light observability/monitoring integrations.

### 6. Mock Camera Mode (P3)

**Behavior:**

- When `MOCK_CAMERA=true`, skip Picamera2 initialization.
- Generate dummy JPEG frames at a simulated FPS to enable local endpoint testing.

---

## Acceptance Criteria

- [ ] `GET /health` always returns 200 with a `status` field set to `healthy`.
- [ ] `GET /ready` returns 200 only when frames are recent and streaming is active; otherwise returns 503 with a `reason` field.
- [ ] `GET /stream.mjpg` streams MJPEG frames with correct MIME type and boundary, or returns 503 if not ready.
- [ ] `GET /metrics` returns JSON including uptime, frame counts, FPS, and configuration values.
- [ ] Environment variables enforce validation rules and fall back to defaults when invalid.
- [ ] `MOCK_CAMERA=true` allows the server to run without CSI hardware while still returning valid endpoints.
- [ ] CORS behavior respects configured origins and defaults to `*` when not explicitly set.

---

## Non-Functional Requirements

**Performance:**

- MJPEG streaming must sustain the configured FPS without excessive CPU overhead on a Raspberry Pi 4/5.

**Reliability:**

- Health/readiness endpoints must remain responsive even when the camera fails to initialize.
- Streaming output should not leak memory over long runtimes.

**Security & Safety:**

- Service is intended for LAN/homelab use and should discourage direct internet exposure.
- CORS configuration must be explicit and documented.

**Operability & Deployment:**

- Docker healthcheck should be compatible with `/health` (or optionally `/ready`).
- Logs should describe camera initialization, errors, and readiness state transitions.
- Container runtime requires device mappings and `/run/udev` mount for camera discovery.

---

## Dependencies

- Raspberry Pi CSI camera hardware with libcamera support
- Picamera2 runtime and Raspberry Pi OS Bookworm-compatible packages
- Flask for HTTP server and routing
- Docker runtime with device mapping access to camera nodes

---

## Open Questions

- Should there be a configurable authentication layer for camera endpoints?
- Do we need an HLS/RTSP output option for wider compatibility beyond MJPEG?

---

## Tasks / Next Steps

- [ ] Define an explicit API schema document for `/ready` and `/metrics` payloads.
- [ ] Consider adding basic auth or token-based access for deployments beyond trusted LANs.
- [ ] Evaluate adding a lightweight snapshot endpoint (`/snapshot.jpg`).

---

## Source References (Current Implementation)

This PRD reflects the current backend implementation in:

- Flask app and endpoints (`pi_camera_in_docker/main.py`)
- Docker deployment and healthcheck setup (`Dockerfile`, `docker-compose.yaml`, `healthcheck.py`)
- Configuration and usage documentation (`README.md`)

---

## Management Mode API Spec

When `APP_MODE=management`, the backend exposes a node management control plane for multi-node operation.

### Node Registry Model

Node objects are persisted through a registry abstraction (initial implementation: file-backed JSON on a mounted volume via `NODE_REGISTRY_PATH`, default `/data/node-registry.json`). Future implementations may swap in DB or service-backed registries without changing HTTP contracts.

**Node fields**

- `id` (string, required, unique)
- `name` (string, required)
- `base_url` (string, required, `http://` or `https://`)
- `auth` (object, required; supported formats only: `{ "type": "none" }` or `{ "type": "bearer", "token": "<api_token>" }`)
  - Deprecated legacy fields (`auth.type=basic`, `auth.username`, `auth.password`, `auth.encoded`) must be migrated to bearer tokens.
- `labels` (object, required)
- `last_seen` (string, required, ISO timestamp)
- `capabilities` (array of strings, required)
- `transport` (string, required: `http` or `docker`)

### Endpoints

#### 1) Node CRUD: `/api/nodes`

- `GET /api/nodes`
  - Returns `{ "nodes": [Node, ...] }`
- `POST /api/nodes`
  - Creates a node from a full Node payload.
  - Returns `201` with created Node.
- `GET /api/nodes/{id}`
  - Returns Node.
  - Returns `404` if not found.
- `PUT /api/nodes/{id}`
  - Accepts partial Node payload and validates merged result.
  - Returns updated Node.
- `DELETE /api/nodes/{id}`
  - Returns `204` when deleted.
  - Returns `404` when missing.

#### 2) Node health/status aggregation: `/api/nodes/{id}/status`

- `GET /api/nodes/{id}/status`
  - For `http` transport, aggregates downstream probe data from `/health`, `/ready`, and `/metrics`.
  - Returns consolidated response:
    - node status and readiness
    - stream availability (`stream_available`)
    - probe payloads/status codes
  - For unsupported transport, returns transport-specific status with `TRANSPORT_UNSUPPORTED` details.

#### 3) Optional control actions: `/api/nodes/{id}/actions/...`

- `POST /api/nodes/{id}/actions/{action}`
  - Optional passthrough for node-side action handlers.
  - Current HTTP behavior forwards to `{base_url}/api/actions/{action}` with JSON body.
  - Returns downstream response/status.

#### 4) Consolidated overview: `/api/management/overview`

- `GET /api/management/overview`
  - Aggregates all registered nodes and status checks.
  - Returns:
    - `summary.total_nodes`
    - `summary.unavailable_nodes`
    - `summary.stream_available_nodes`
    - per-node status entries, including errors for unreachable/unauthorized nodes.

### Validation & Error Schema

All management API errors follow:

```json
{
  "error": {
    "code": "VALIDATION_ERROR|NODE_NOT_FOUND|NODE_UNREACHABLE|NODE_UNAUTHORIZED|TRANSPORT_UNSUPPORTED",
    "message": "human-readable message",
    "node_id": "optional-node-id",
    "details": {},
    "timestamp": "ISO-8601 timestamp"
  }
}
```

Special cases:

- `NODE_UNREACHABLE` (HTTP 503): downstream node not reachable / timeout / network failure.
- `NODE_UNAUTHORIZED` (HTTP 401): downstream node returned auth failure (`401`/`403`).
- `VALIDATION_ERROR` (HTTP 400): malformed node payload or unsupported field values.
