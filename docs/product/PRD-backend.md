# PRD (Backend): motion-in-ocean

## Scope

This document contains backend-specific requirements only. For shared problem statement, cross-cutting goals, and shared constraints/non-goals, see [PRD-core.md](PRD-core.md).

## Backend Requirements

### 1. MJPEG Streaming Endpoint (P1)

**Endpoint:** `GET /stream.mjpg`

**Behavior:**

- Streams multipart MJPEG frames with `boundary=frame`.
- Returns HTTP `503` if backend is not ready to serve frames.
- Sends cache-control headers to avoid stale stream caching.

### 2. Health & Readiness Probes (P1)

**Endpoints:**

- `GET /health` → liveness endpoint; returns `200` when server process is up.
- `GET /ready` → readiness endpoint; returns `200` only when recording has started and frame freshness is within threshold.

**Readiness details:**

- Returns `503` with diagnostic reason when:
  - recording has not started,
  - no frame has been captured,
  - or frame age exceeds `MAX_FRAME_AGE_SECONDS`.

### 3. Raspberry Pi CSI Camera Capture (P1)

- Uses Picamera2/libcamera for headless capture.
- Supports configured FPS limiting when enabled.
- Starts/stops recording cleanly across process lifecycle.

### 4. Environment-Driven Configuration (P1)

- `RESOLUTION` (default `640x480`, max `4096x4096`)
- `FPS` (default `0`, max `120`)
- `JPEG_QUALITY` (default `100`)
- `CORS_ORIGINS` (default `*` unless configured)
- `MOCK_CAMERA` (default `false`)
- `MAX_FRAME_AGE_SECONDS` (default `10`)

Invalid values must fall back to safe defaults.

### 5. Metrics Endpoint (P2)

**Endpoint:** `GET /metrics`

Returns JSON for lightweight observability (uptime, FPS, frame counters, frame age, configured resolution, timestamp).

### 6. Mock Camera Mode (P3)

When `MOCK_CAMERA=true`, backend skips CSI initialization and emits synthetic JPEG frames for local/test validation.

## Backend API Requirements (Management Mode)

When `APP_MODE=management`, backend exposes control-plane APIs.

### Node Registry Model

Node schema fields:

- `id` (required, unique)
- `name` (required)
- `base_url` (required, `http://` or `https://`)
- `auth` (required; `{ "type": "none" }` or `{ "type": "bearer", "token": "..." }`)
- `labels` (required object)
- `last_seen` (required ISO timestamp)
- `capabilities` (required string array)
- `transport` (required: `http` or `docker`)

Persistence uses registry abstraction (initially file-backed via `NODE_REGISTRY_PATH`).

### Endpoints

- `GET /api/nodes`
- `POST /api/nodes`
- `GET /api/nodes/{id}`
- `PUT /api/nodes/{id}`
- `DELETE /api/nodes/{id}`
- `GET /api/nodes/{id}/status`
- `POST /api/nodes/{id}/actions/{action}`
- `GET /api/management/overview`

### Error Schema

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

## Backend Acceptance Criteria

- [ ] `/health` returns `200` with healthy liveness payload whenever process is running.
- [ ] `/ready` returns `200` only for active + fresh frame state; otherwise `503` with reason.
- [ ] `/stream.mjpg` serves valid MJPEG multipart stream or `503` when not ready.
- [ ] `/metrics` returns JSON with runtime counters and configuration-facing values.
- [ ] Environment variable validation applies safe defaults for invalid inputs.
- [ ] `MOCK_CAMERA=true` supports hardware-free startup and endpoint behavior.
- [ ] Management endpoints enforce node schema and return standardized errors.
