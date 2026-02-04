# PRD (Frontend): motion-in-ocean

## TL;DR

This PRD defines the frontend requirements for motion-in-ocean: a lightweight web UI that renders the MJPEG stream, provides refresh/fullscreen controls, and exposes stream status and stats with resilient polling/retry behavior. For camera capture, health/readiness, and deployment details, see [PRD-backend.md](PRD-backend.md).

---

## Problem Statement

Operators need a simple, reliable web UI to view the Raspberry Pi CSI camera stream without additional tooling. The UI must make it obvious when the stream is connected, expose a minimal control set, and remain resilient to transient stream or backend readiness failures.

---

## Goals / Success Metrics

- **Clear stream viewing experience:** Users can load the UI and immediately see the live MJPEG stream.
- **Low-friction controls:** Users can refresh the stream and enter fullscreen without confusion.
- **Operational visibility:** Users can read current status and basic stats (FPS, frame count, uptime, resolution).
- **Resilient UX:** The UI retries stream loading and status polling when the backend is temporarily unavailable.

---

## User Stories (Frontend)

- As a viewer, I want a simple web UI with fullscreen and refresh controls so that I can reliably access the stream.
- As a user, I want to see connection status and basic stream stats so that I can confirm the camera is healthy.
- As a viewer, I want the UI to recover automatically if the stream drops.

---

## Prioritized Functional Requirements

| Priority | Feature | Description |
| --- | --- | --- |
| P1 | Web UI for Live Stream | Serve a UI at `/` that renders the MJPEG stream and basic stream stats. |
| P1 | Stream View + Controls | Provide refresh and fullscreen controls for the stream viewport. |
| P2 | Stream Stats & Status UI | Show connection status, frame metrics, and configuration badges in the UI. |
| P2 | Resilience & Retry | UI retries stats fetching and stream reloads with backoff on error. |

---

## Functional Requirements

### 1. Web UI for Live Stream (P1)

**Endpoint:** `GET /`

**Behavior:**
- Displays the MJPEG stream in a responsive layout.
- Includes a connection status indicator.
- Provides refresh and fullscreen controls.
- Displays stream stats (FPS, frame count, uptime, resolution).

### 2. Stream Stats & Status UI (P2)

**Behavior:**
- Polls `/ready` on an interval to update metrics.
- Shows “Connecting”/“Connected”/“Disconnected” status.
- Displays a collapsible stats panel on small screens.

### 3. Resilience & Retry (P2)

**Behavior:**
- UI retries stats requests with exponential backoff on failure.
- UI schedules stream reload attempts on stream errors with a separate backoff policy.

---

## Acceptance Criteria

- [ ] Web UI renders the stream and loads quickly on LAN networks.
- [ ] Refresh control reloads the stream without a full page refresh.
- [ ] Fullscreen control toggles the stream view as expected.
- [ ] UI shows connection status and basic stream stats pulled from `/ready`.
- [ ] UI retries failed `/ready` requests with backoff and updates the status accordingly.
- [ ] UI recovers from stream errors by attempting reloads with backoff.

---

## Non-Functional Requirements

**Responsiveness:**
- UI should be usable on mobile and desktop layouts.

**Performance:**
- UI polling interval defaults to a lightweight cadence (2 seconds).

---

## Open Questions

- Should the UI allow user-configurable polling intervals or a “low-bandwidth” mode?
- Should the UI include a quick snapshot download button?

---

## Tasks / Next Steps

- [ ] Add UI screenshots to documentation.
- [ ] Consider a “low-bandwidth” toggle for slower networks.

---

## Source References (Current Implementation)

This PRD reflects the current frontend implementation in:
- Web UI template (`pi_camera_in_docker/templates/index.html`)
- UI behavior and polling logic (`pi_camera_in_docker/static/js/app.js`)
- UI styles (`pi_camera_in_docker/static/css/style.css`, `pi_camera_in_docker/static/css/tabs-config.css`)
