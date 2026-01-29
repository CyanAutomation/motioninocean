# PRD: motion-in-ocean (Raspberry Pi CSI Camera Streaming)

## TL;DR

This PRD defines the complete product requirements for the motion-in-ocean service: a Docker-first Raspberry Pi CSI camera streaming stack with MJPEG output, health/readiness probes, a lightweight web UI, and configuration via environment variables. The project targets homelab deployments and emphasizes reliable camera startup, observability, and minimal dependencies.

---

## Problem Statement

Running a Raspberry Pi CSI camera inside Docker is non-trivial due to libcamera dependencies, device mappings, and the need for reliable health checks. Homelab users want a simple, containerized service that streams video reliably, exposes clear health/readiness signals, and can be deployed without custom host-side software. Without a single PRD, core behaviors and expectations are scattered across README and code, making it harder to maintain or extend.

---

## Quick Reference for AI Search

This document covers the following topics that agents frequently search for:

- **HTTP endpoints and status semantics** (/, /stream.mjpg, /health, /ready, /metrics)
- **Environment configuration** (RESOLUTION, FPS, EDGE_DETECTION, MOCK_CAMERA, CORS_ORIGINS, JPEG_QUALITY)
- **Streaming behavior** (MJPEG output, frame age readiness, reconnection strategy)
- **Docker and deployment expectations** (device mappings, healthcheck script, compose setup)
- **Web UI behaviors** (fullscreen, refresh, stats panel, connection state)

### Search Keywords

motion-in-ocean PRD, MJPEG stream, readiness probe, mock camera, CORS, Raspberry Pi CSI, Docker camera streaming, healthcheck, homelab camera UI

---

## Goals / Success Metrics

- **Reliable streaming:** The service consistently exposes a working MJPEG stream when the camera is available.
- **Predictable health semantics:** `/health` always indicates service liveness; `/ready` only indicates readiness when frames are flowing.
- **Simple deployment:** Users can deploy with a Docker image and minimal host configuration (device mappings + env file).
- **Operational clarity:** Users can inspect status, FPS, and basic metrics via `/ready` and `/metrics`.
- **Low-friction UI:** The built-in UI provides a clear stream view, refresh controls, and stream stats.

---

## User Stories

- As a homelab operator, I want a Docker image that streams my Pi CSI camera so that I can view it on my network without installing host software.
- As a deployer, I want explicit health and readiness endpoints so that Docker and monitoring tools can detect failure states.
- As a viewer, I want a simple web UI with fullscreen and refresh controls so that I can reliably access the stream.
- As a developer, I want mock mode to validate the service without camera hardware.
- As an integrator, I want MJPEG output and CORS controls so that I can embed the stream in dashboards or other tools.

---

## Prioritized Functional Requirements

| Priority | Feature | Description |
| --- | --- | --- |
| P1 | MJPEG Streaming Endpoint | Provide a stable MJPEG stream at `/stream.mjpg` with appropriate headers and a 503 response if not ready. |
| P1 | Health & Readiness Probes | `/health` returns 200 if the server is running; `/ready` returns 200 only when frames are flowing and not stale, else 503 with diagnostic details. |
| P1 | Raspberry Pi CSI Camera Capture | Use Picamera2/libcamera to capture frames in a headless container, with required device mappings. |
| P1 | Environment-Driven Configuration | Support resolution, FPS, JPEG quality, edge detection, CORS origins, and mock mode via environment variables. |
| P1 | Web UI for Live Stream | Serve a UI at `/` that renders the MJPEG stream and basic stream stats. |
| P2 | Metrics Endpoint | Expose `/metrics` with uptime, frame counts, FPS, and configuration details. |
| P2 | Stream Stats & Status UI | Show connection status, frame metrics, and configuration badges in the UI. |
| P2 | Resilience & Retry | UI should retry stats fetching and stream reloads with backoff on error. |
| P3 | Edge Detection Option | Enable Canny edge detection when OpenCV is available and the flag is set. |
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
- Use Picamera2 and libcamera with BGR format for compatibility with edge detection.
- Support FPS limiting when configured.
- Start recording via JPEG encoder and stream output.
- Gracefully shut down recording on exit.

### 4. Environment-Driven Configuration (P1)

**Required environment variables:**
- `RESOLUTION` (default `640x480`, max `4096x4096`)
- `FPS` (default `0` for camera default, max 120)
- `JPEG_QUALITY` (default `100`)
- `EDGE_DETECTION` (default `false`)
- `CORS_ORIGINS` (default `*` unless set)
- `MOCK_CAMERA` (default `false`)
- `MAX_FRAME_AGE_SECONDS` (default `10`)

**Validation rules:**
- Invalid or out-of-range values fall back to safe defaults.
- If edge detection is requested without OpenCV, the service logs a warning and disables the feature.

### 5. Web UI for Live Stream (P1)

**Endpoint:** `GET /`

**Behavior:**
- Displays the MJPEG stream in a responsive layout.
- Includes connection status indicator.
- Provides refresh and fullscreen controls.
- Displays stream stats (FPS, frame count, uptime, resolution, edge detection status).

### 6. Metrics Endpoint (P2)

**Endpoint:** `GET /metrics`

**Behavior:**
- Returns JSON with uptime, FPS, frame counts, last frame age, resolution, edge detection status, and timestamp.
- Intended for light observability/monitoring integrations.

### 7. Stream Stats & Status UI (P2)

**Behavior:**
- Polls `/ready` on an interval to update metrics.
- Shows “Connecting”/“Connected”/“Disconnected” status.
- Displays a collapsible stats panel on small screens.

### 8. Resilience & Retry (P2)

**Behavior:**
- UI retries stats requests with exponential backoff on failure.
- UI schedules stream reload attempts on stream errors with a separate backoff policy.

### 9. Edge Detection Option (P3)

**Behavior:**
- When enabled and OpenCV is available, applies Canny edge detection to frames before encoding.
- When unavailable, service logs a warning and continues with unmodified frames.

### 10. Mock Camera Mode (P3)

**Behavior:**
- When `MOCK_CAMERA=true`, skip Picamera2 initialization.
- Generate dummy JPEG frames at a simulated FPS to enable local UI and endpoint testing.

---

## Acceptance Criteria

- [ ] `GET /health` always returns 200 with a `status` field set to `healthy`.
- [ ] `GET /ready` returns 200 only when frames are recent and streaming is active; otherwise returns 503 with a `reason` field.
- [ ] `GET /stream.mjpg` streams MJPEG frames with correct MIME type and boundary, or returns 503 if not ready.
- [ ] `GET /metrics` returns JSON including uptime, frame counts, FPS, and configuration values.
- [ ] Web UI renders the stream, has refresh and fullscreen controls, and shows stats with connection status.
- [ ] Environment variables enforce validation rules and fall back to defaults when invalid.
- [ ] `MOCK_CAMERA=true` allows the server to run without CSI hardware while still returning valid endpoints.
- [ ] CORS behavior respects configured origins and defaults to `*` when not explicitly set.

---

## Non-Functional Requirements

**Performance:**
- MJPEG streaming must sustain the configured FPS without excessive CPU overhead on a Raspberry Pi 4/5.
- UI polling interval defaults to a lightweight cadence (2 seconds).

**Reliability:**
- Health/readiness endpoints must remain responsive even when the camera fails to initialize.
- Streaming output should not leak memory over long runtimes.

**Security & Safety:**
- Service is intended for LAN/homelab use and should discourage direct internet exposure.
- CORS configuration must be explicit and documented.

**Operability:**
- Docker healthcheck should be compatible with `/health`.
- Logs should describe camera initialization, errors, and readiness state transitions.

---

## Dependencies

- Raspberry Pi CSI camera hardware with libcamera support
- Picamera2 runtime and Raspberry Pi OS Bookworm-compatible packages
- Flask for HTTP server and routing
- Optional OpenCV (`opencv-python-headless`) for edge detection
- Docker runtime with device mapping access to camera nodes

---

## Open Questions

- Should there be a configurable authentication layer for the web UI and stream?
- Do we need an HLS/RTSP output option for wider compatibility beyond MJPEG?
- Should the UI allow custom polling intervals or a “low-bandwidth” mode?

---

## Tasks / Next Steps

- [ ] Add this PRD to documentation navigation (README or docs index).
- [ ] Define an explicit API schema document for `/ready` and `/metrics` payloads.
- [ ] Consider adding basic auth or token-based access for deployments beyond trusted LANs.
- [ ] Evaluate adding a lightweight snapshot endpoint (`/snapshot.jpg`).

---

## Source References (Current Implementation)

This PRD reflects the current implementation in:
- Flask app and endpoints (`pi_camera_in_docker/main.py`)
- Web UI template and behavior (`pi_camera_in_docker/templates/index.html`, `pi_camera_in_docker/static/js/app.js`)
- Docker deployment and healthcheck setup (`Dockerfile`, `docker-compose.yaml`, `healthcheck.py`)
- Configuration and usage documentation (`README.md`)
