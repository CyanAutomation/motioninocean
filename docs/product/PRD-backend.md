# PRD (Backend): motion-in-ocean

## Scope

This document contains backend-specific requirements only. For shared problem statement,
cross-cutting goals, and shared constraints/non-goals, see [PRD-core.md](PRD-core.md).

## Backend Requirements

### Multi-Host Architecture Overview

```mermaid
graph LR
    subgraph "Cameras"
        WC1["Webcam Host 1<br/>(APP_MODE=webcam)"]
        WC2["Webcam Host 2<br/>(APP_MODE=webcam)"]
    end
    subgraph "Management"
        MGMT["Management Host<br/>(APP_MODE=management)"]
    end
    subgraph "Persistence"
        REG["Node Registry<br/>(JSON file)"]
    end
    subgraph "User"
        BR["Browser"]
    end

    WC1 -->|POST /api/discovery/announce| MGMT
    WC2 -->|POST /api/discovery/announce| MGMT
    MGMT -->|Upserts| REG
    BR -->|GET /nodes<br/>POST /nodes/{id}| MGMT
    MGMT -->|Management aggregation contract:<br/>GET /api/status (required)| WC1
    MGMT -->|Management aggregation contract:<br/>GET /api/status (required)| WC2
    MGMT -.->|Operator diagnostics only:<br/>GET /health, /ready, /metrics| WC1
    MGMT -.->|Operator diagnostics only:<br/>GET /health, /ready, /metrics| WC2
```

**Key flows:**

- Webcams announce themselves to management (discovery)
- Management status aggregation contract probes `GET /api/status` on each approved node
- `/health`, `/ready`, and `/metrics` are operator-facing diagnostics and are not part of management health classification
- Registry persists node metadata with atomic file locking

---

### 1. MJPEG Streaming Endpoint (P1)

**Endpoint:** `GET /stream.mjpg`

**Behavior:**

- Streams multipart MJPEG frames with `boundary=frame`.
- Returns HTTP `503` if backend is not ready to serve frames.
- Sends cache-control headers to avoid stale stream caching.

#### Streaming Pipeline

```mermaid
sequenceDiagram
    participant Encoder as libcamera<br/>encoder
    participant Buffer as FrameBuffer
    participant Stats as StreamStats
    participant Client as HTTP client(s)

    loop frame capture
        Encoder->>Buffer: write(frame)
        Buffer->>Buffer: notify Condition<br/>for readers
    end

    Client->>Stats: snapshot()
    Stats->>Stats: acquire Lock
    Stats-->>Client: {frame_count, fps, age}
    note over Stats: Monotonic clock prevents<br/>system clock skew
```

**Concurrency details:**

- Frame writes use `Condition` to efficiently notify waiting readers
- Stats snapshot holds `Lock` only long enough to read counters
- FPS calculated from rolling 30-frame window (monotonic timestamps)
- Optional frame throttling via `_target_frame_interval`
- Connection limit enforced via `ConnectionTracker`
- Oversized frames dropped if `> MAX_FRAME_SIZE`

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

### Security: SSRF Protection

```mermaid
flowchart LR
    A["HTTP Request to<br/>/api/nodes/{id}/status"] --> B["Parse IP from<br/>node.base_url"]
    B --> C{{"IP in private set?<br/>RFC1918, loopback,<br/>link-local, reserved"}}
    C -->|Yes| D{{"MOTION_IN_OCEAN<br/>_ALLOW_PRIVATE_IPS<br/>=true?"}}
    C -->|No| E["Proxy request"]
    D -->|Yes| E
    D -->|No| F["403 Forbidden<br/>SSRF_BLOCKED"]
    E --> G["HTTP GET with<br/>bearer token"]
    G --> H["Response or<br/>error classification"]
    F --> I["Return error"]
    H --> I
```

**Configuration:**

- Default: `MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS=false` (production-safe)
- For LANs: Set to `true`
- Bearer token in `Authorization: Bearer <token>` header
- Error codes: `SSRF_BLOCKED`, `NODE_UNAUTHORIZED`, `NODE_UNREACHABLE`

---

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

#### Node Discovery Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Announced: Webcam announces

    Announced: source="discovered"
    Announced: approved=false

    Announced --> Approved: Admin approves<br/>POST /api/nodes/{id}/discovery/approve

    Approved: source="discovered"
    Approved: approved=true

    Announced --> Deleted: Admin deletes
    Approved --> Deleted: Admin deletes

    Deleted: [*]

    note right of Announced
        Registration pending;
        hidden from /api/management/overview
    end note

    note right of Approved
        Ready for aggregation;
        /api/nodes/{id}/status queryable
    end note
```

**Atomicity:** Registry lock ensures concurrent announcements from multiple webcams are serialized.

#### Discovery Sequence Flow

```mermaid
sequenceDiagram
    participant Webcam as Webcam<br/>Announcer
    participant Mgmt as Management<br/>Backend
    participant Reg as Registry

    loop every DISCOVERY_ANNOUNCE_INTERVAL_SECONDS
        Webcam->>Webcam: Generate stable node_id<br/>(hostname + MAC hash)
        Webcam->>Mgmt: POST /api/discovery/announce
        Mgmt->>Mgmt: Validate bearer token
        Mgmt->>Mgmt: Parse IP address
        Mgmt->>Mgmt: SSRF check (unless<br/>ALLOW_PRIVATE_IPS=true)
        alt SSRF blocked
            Mgmt-->>Webcam: 403 Forbidden
        else SSRF allowed
            Mgmt->>Reg: Acquire lock, upsert
            note over Reg: Creates new node or<br/>updates last_seen
            Reg-->>Mgmt: Locked and written
            Mgmt-->>Webcam: 200 OK
        end
    end
```

**Resilience:** Announcements repeat (not one-shot); failures are retried on next cycle.

### Endpoints

- `GET /api/nodes`
- `POST /api/nodes`
- `GET /api/nodes/{id}`
- `PUT /api/nodes/{id}`
- `DELETE /api/nodes/{id}`
- `GET /api/nodes/{id}/status`
- `POST /api/nodes/{id}/actions/{action}`
- `GET /api/management/overview`

#### Management Status Aggregation

```mermaid
sequenceDiagram
    participant UI as Client / UI
    participant Mgmt as Management<br/>Backend
    participant Nodes as Webcam<br/>Nodes

    UI->>Mgmt: GET /api/management/overview
    Mgmt->>Mgmt: Read approved nodes from registry
    note over Mgmt: Acquire lock, filter approved=true

    par Parallel status queries
        Mgmt->>Nodes: GET /api/nodes/{id1}/status
        Nodes-->>Mgmt: 200 {stream_available,<br/>camera_active, fps}
    and
        Mgmt->>Nodes: GET /api/nodes/{id2}/status
        Nodes-->>Mgmt: Connection timeout
    and
        Mgmt->>Nodes: GET /api/nodes/{id3}/status
        Nodes-->>Mgmt: 401 Unauthorized
    end

    Mgmt->>Mgmt: Classify errors:<br/>UNREACHABLE, UNAUTHORIZED,<br/>INVALID_RESPONSE
    Mgmt->>Mgmt: Aggregate into summary
    Mgmt-->>UI: 200 {nodes: [...],<br/>summary, errors}
```

**Status Aggregation Flowchart:**

```mermaid
flowchart TD
    A["GET /api/management/overview"] --> B["Read registry lock,<br/>collect approved nodes"]
    B --> C["For each node"]
    C --> D{{"Node<br/>transport?"}}
    D -->|http| E["Parse base_url IP"]
    D -->|docker| F["Build container path"]
    E --> G{{"SSRF<br/>check"}}
    G -->|Blocked| H["Error:<br/>SSRF_BLOCKED"]
    G -->|Allowed| I["HTTP GET /api/status"]
    F --> J["Docker exec"]
    I --> K{{"Response<br/>ok?"}}
    K -->|timeout| L["Error:<br/>UNREACHABLE"]
    K -->|401/403| M["Error:<br/>UNAUTHORIZED"]
    K -->|200| N["Parse response"]
    K -->|invalid JSON| O["Error:<br/>INVALID_RESPONSE"]
    J --> N
    H --> P["Aggregate all results"]
    L --> P
    M --> P
    N --> P
    O --> P
    P --> Q["Return overview<br/>with summary stats"]
```

**Performance note:** Queries execute in parallel with per-node timeout to prevent slow aggregation.

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

### API Test Mode (Deterministic Status Validation)

Webcam mode supports deterministic status simulation for management validation.

#### Environment Variables

- `API_TEST_MODE_ENABLED` (`true|false`, default `false`)
- `API_TEST_CYCLE_INTERVAL_SECONDS` (positive float, default `5`)
- `MANAGEMENT_AUTH_TOKEN` (required when protecting `/api/status` and `/api/actions/*`)

#### Webcam Action Endpoints

- `POST /api/actions/api-test-start`
  - Optional body: `{ "interval_seconds": <positive number>, "scenario_order": [0,1,2] }`
  - Starts deterministic transitions.
- `POST /api/actions/api-test-stop`
  - Body: `{}`
  - Stops automatic transitions (state remains fixed).
- `POST /api/actions/api-test-step`
  - Body: `{}`
  - Advances exactly one deterministic state; stays paused.
- `POST /api/actions/api-test-reset`
  - Body: `{}`
  - Resets to state index `0`; stays paused.

#### Management Passthrough Endpoint

- `POST /api/nodes/{id}/actions/{action}`
  - Forwards to node `POST /api/actions/{action}` with same JSON body.
  - Returns `{ node_id, action, status_code, response }`.

#### Expected Default Scenario Sequence

1. `ok`: `stream_available=true`, `camera_active=true`, `fps=24.0`
2. `degraded`: `stream_available=false`, `camera_active=true`, `fps=0.0`
3. `degraded`: `stream_available=false`, `camera_active=false`, `fps=0.0`

#### Operator Checklist

- [ ] Confirm all three deterministic states appear in management UI/API.
- [ ] Confirm interval-driven transition advances state index.
- [ ] Confirm `api-test-step` changes state immediately and pauses.
- [ ] Confirm `api-test-stop` keeps current state fixed.
- [ ] Confirm `api-test-reset` restores state index `0`.
- [ ] Confirm protected action routes still require valid bearer auth.

## Backend Acceptance Criteria

- [ ] `/health` returns `200` with healthy liveness payload whenever process is running.
- [ ] `/ready` returns `200` only for active + fresh frame state; otherwise `503` with reason.
- [ ] `/stream.mjpg` serves valid MJPEG multipart stream or `503` when not ready.
- [ ] `/metrics` returns JSON with runtime counters and configuration-facing values.
- [ ] Environment variable validation applies safe defaults for invalid inputs.
- [ ] `MOCK_CAMERA=true` supports hardware-free startup and endpoint behavior.
- [ ] Management endpoints enforce node schema and return standardized errors.
