# PRD (Frontend): motion-in-ocean

## Scope

This document contains frontend-specific requirements only. For shared problem statement, cross-cutting goals, and shared constraints/non-goals, see [PRD-core.md](PRD-core.md).

## Frontend Requirements

### 1. Stream Viewer UI (P1)

**Endpoint:** `GET /`

- Renders live MJPEG stream in responsive layout.
- Exposes connection status indicator.
- Provides refresh and fullscreen controls.

#### Webcam Viewer State Machine

```mermaid
stateDiagram-v2
    [*] --> Connecting: Load page
    
    Connecting: Poll /metrics
    Connecting: retry backoff: 2s
    
    Connecting --> Connected: /metrics 200 OK
    Connecting --> Disconnected: /metrics error +<br/>consecutiveFailures > threshold
    
    Connected: Display stats
    Connected: Config polling active
    Connected: Setup detection active
    
    Connected --> Connected: /metrics 200 OK<br/>reset consecutiveFailures
    Connected --> Disconnected: /metrics error<br/>+consecutiveFailures++
    
    Disconnected: Show disconnected state
    Disconnected: retry backoff<br/>increases to max 30s
    
    Disconnected --> Connected: /metrics 200 OK
    Disconnected --> Disconnected: /metrics error<br/>backoff continues
    
    Disconnected --> Connecting: User clicks refresh
    Connected --> Connecting: User clicks refresh
    
    note right of Connecting
        Initial state; immediate polling
        2 second interval
    end note
    
    note right of Connected
        Active streaming; UI responsive
        Separate intervals for config, setup
    end note
    
    note right of Disconnected
        Exponential backoff: 2s → 4s → 8s → 30s
        Manual refresh overrides backoff
    end note
```

**Polling intervals:**
- Stats refresh: 2-30s (exponential backoff on failure)
- Config polling: 5s (independent)
- Setup detection: 5s (independent, during idle)

### 2. Status & Stats Presentation (P2)

- Polls backend readiness/status data on interval.
- Shows user-facing state transitions (e.g., Connecting, Connected, Disconnected).
- Displays stream stats such as FPS, frame count, uptime, and resolution.
- Keeps stats panel usable on small screens.

#### Webcam UI Stats Polling

```mermaid
flowchart TD
    A["updateStats() triggered<br/>on interval"] --> B["Fetch /metrics"]
    B --> C{{"Response<br/>ok?"}}
    C -->|200 OK| D["Parse stats:<br/>fps, frames, age, uptime"]
    D --> E["Update UI display"]
    E --> F["Reset consecutive<br/>failures to 0"]
    F --> G["Schedule next poll<br/>at base interval"]
    C -->|Error| H["consecutive<br/>failures++"]
    H --> I{{"failures ><br/>threshold?"}}
    I -->|Yes| J["Transition to<br/>Disconnected"]
    I -->|No| K["Calculate backoff<br/>delay"]
    J --> L["Show error state"]
    K --> L
    L --> M["Schedule retry"]
```

**Config & setup polling are independent:**
- Config polling: `/api/config` every 5s (resolution, FPS, JPEG quality changes)
- Setup detection: Device discovery endpoint every 5s (during setup tab)
- All three polling streams use shared `updateInterval` but separate timers

### 3. Resilience & Retry Behavior (P2)

- Retries failed status polling with backoff.
- Retries stream reload on media errors with independent backoff policy.
- Surfaces degraded state without blocking later automatic recovery.

#### Stream Reload Retry Logic

```mermaid
flowchart TD
    A["Stream media error<br/>detected"] --> B["Increment stream<br/>retry counter"]
    B --> C{{"Retries <br/>max count?"}}
    C -->|Yes| D["Calculate exponential<br/>backoff delay"]
    D --> E["Schedule stream<br/>reload"]
    E --> F["Show 'reconnecting'<br/>indicator"]
    F --> G["Wait delay"]
    G --> H["Reload stream<br/>GET /stream.mjpg"]
    H --> I{{"Stream<br/>ok?"}}
    I -->|Yes| J["Reset retry counter"]
    J --> K["Resume normal playback"]
    C -->|No| L["Show permanent<br/>error state"]
    I -->|No| M["Loop: retry counter++"]
    M --> D
    L --> N["Display troubleshooting<br/>tips"]
```

**Backoff policy:** 2s, 4s, 8s, 16s, 30s (exponential, max 30s)
**Stream polling:** Independent from stats polling (separate intervals)

---

## Management UI (dashboard.html / management.js)

When accessing `GET /` on management host, displays node management interface.

### Node Management Interface

**Features:**
- Node registration form (manual or discovered)
- Node table with approval/deletion controls
- Status polling for each node (independent)
- Diagnostic panel with remediation hints

#### Management Node Status Polling

```mermaid
sequenceDiagram
    participant UI as Management UI
    participant Mgmt as Management<br/>Backend
    participant Nodes as Webcam<br/>Nodes

    UI->>UI: Load node list or<br/>refresh clicked
    UI->>Mgmt: GET /api/nodes
    Mgmt-->>UI: [{id, name, base_url,<br/>approved, ...}]
    
    UI->>UI: Set up polling loop
    loop every STATUS_POLL_INTERVAL
        alt statusRefreshInFlight check
            UI->>Mgmt: GET /api/nodes/{ids}/status<br/>(batch or parallel)
            Mgmt->>Nodes: Proxy GET /api/status<br/>to each node
            Nodes-->>Mgmt: Response or error
            Mgmt-->>UI: Aggregated response
            UI->>UI: statusRefreshInFlight=false
        else retry pending (statusRefreshPending)
            UI->>UI: Defer until current<br/>refresh completes
            note over UI: Prevents request<br/>storm
        end
        UI->>UI: Update node rows<br/>with new status
        UI->>UI: Schedule next poll
    end
```

**Deduplication logic:**
- `statusRefreshInFlight=true` during fetch
- `statusRefreshPending=true` if new poll requested during fetch
- Next cycle processes pending poll
- Prevents concurrent requests to backend

#### Node CRUD Workflow

```mermaid
flowchart TD
    A["User action:<br/>Create/Update/Delete"] --> B{{"Action<br/>type?"}}
    
    B -->|Create| C["Fill form:<br/>ID, name, base_url,<br/>auth,labels"]
    C --> D["Validate input<br/>on client"]
    D --> E{{"Valid?"}}
    E -->|No| F["Show validation<br/>errors"]
    F --> C
    E -->|Yes| G["POST /api/nodes<br/>with JSON body"]
    
    B -->|Update| H["Edit selected node<br/>fields"]
    H --> D
    
    B -->|Delete| I["Confirmation<br/>dialog"]
    I --> J{{"Confirm?"}}
    J -->|No| K["Cancel"]
    J -->|Yes| L["DELETE /api/nodes/{id}"]
    
    G --> M{{"Server<br/>ok?"}}
    L --> M
    M -->|201/200| N["Refresh node list"]
    M -->|error| O["Show error<br/>with details"]
    O --> P{{"Retry?"}}
    P -->|Yes| C
    P -->|No| Q["Dismiss"]
    
    N --> R["Update UI<br/>node table"]
    Q --> S["End"]
    K --> S
```

---

## Frontend API Dependencies

Frontend integrates with backend APIs:

- `GET /stream.mjpg`
- `GET /ready`
- `GET /metrics` (or readiness payload fields used for stats)

See [PRD-backend.md](PRD-backend.md) for API semantics and payload expectations.

## Frontend Acceptance Criteria

- [ ] UI loads and renders stream on LAN in normal operating conditions.
- [ ] Refresh control reloads stream without full page refresh.
- [ ] Fullscreen control toggles stream view correctly.
- [ ] UI status reflects backend readiness/connection changes.
- [ ] UI displays expected stream stats from backend APIs.
- [ ] Polling failures trigger backoff retry and eventual recovery when backend returns.
- [ ] Stream errors trigger reload attempts with backoff.
