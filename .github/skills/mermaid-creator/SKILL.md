---
name: mermaid-creator
description: Creates clear, semantically meaningful Mermaid diagrams for motion-in-ocean PRDs, workflows, and architecture; optimized for AI comprehension first and human readability second.
owner: motion-in-ocean team
last-reviewed: 2026-08-05
category: Documentation
compatible-repo-areas:
  - docs/
  - jsdoc.json
  - Makefile
  - README.md
---

## Purpose

Create Mermaid diagrams that clarify camera streaming architecture, health/readiness state transitions, API workflows, frame capture pipelines, and deployment scenarios. Diagrams serve both developers (architecture understanding, state machines, data flows) and operators (deployment clarity, troubleshooting visual reference). Diagrams must use project-accurate terminology and be validated in rendering before commit.

## Scope and trigger conditions

Apply this skill when:

- Creating or updating diagrams in [PRD-backend.md](../../PRD-backend.md), [PRD-frontend.md](../../PRD-frontend.md), [DEPLOYMENT.md](../../DEPLOYMENT.md), or [README.md](../../README.md)
- Translating plain-language requirements into Mermaid syntax (e.g., "readiness depends on camera recording AND frames not stale")
- Refactoring ASCII art diagrams into semantic Mermaid structures (e.g., DEPLOYMENT.md ASCII architecture)
- Documenting state machines (`/health` always 200 vs `/ready` conditional availability)
- Visualizing API workflows (node CRUD, status probing, aggregation)
- Illustrating frame capture pipelines (Picamera2 → JpegEncoder → FrameBuffer → stream/snapshot)

Do NOT use this skill for:

- Decorative or exploratory diagrams that don't map to actual architecture
- Diagrams that diverge from PRD terminology or misrepresent system behavior
- Overly detailed flowcharts that obscure the core intent
- High-level design conceptual diagrams (use sketches or wireframes instead)

## Required inputs

- Clear understanding of what concept/workflow needs visualization (state machine, data flow, API sequence, architecture)
- Familiarity with motion-in-ocean terminology (RECORDING, STALE, /health, /ready, Bearer Token, FileNodeRegistry, etc.)
- Access to source docs (PRD-backend.md, PRD-frontend.md, DEPLOYMENT.md) to validate terminology
- Knowledge of target audience (developers, operators, or both)
- Mermaid syntax reference ([mermaid.live](https://mermaid.live) for testing)

## Step-by-step workflow

### 1. Select Diagram Type

Match diagram type to intent—never force content into wrong diagram type:

- **`stateDiagram-v2`** (state machine): Health/readiness lifecycle, state transitions (e.g., STOPPED → INITIALIZING → RECORDING → STALE)
- **`graph TD`** (flowchart, top-down): Architecture, multi-host deployment, component hierarchy
- **`graph LR`** (flowchart, left-to-right): Data flow, frame capture pipeline, linear processes
- **`sequenceDiagram`** (sequence): API workflows, node registry CRUD, multi-actor interactions (management → webcam)
- **`erDiagram`** (entity relationship): Data models and relationships (use sparingly in motion-in-ocean)

### 2. Use Accurate, Deterministic Labels

- **Terminology must match** [PRD-backend.md](../../PRD-backend.md), [PRD-frontend.md](../../PRD-frontend.md), codebase
- **Accurate labels:** `RECORDING`, `STALE`, `recording_started`, `MAX_FRAME_AGE_SECONDS`, `Bearer Token Auth`, `/ready`, `FileNodeRegistry`
- **Avoid ambiguous labels:** Don't use "Check" or "Ready?"—be explicit: "Frames fresh?" or "Frame age < MAX_FRAME_AGE_SECONDS"
- **Node IDs must be deterministic:** No random suffixes, timestamps, or placeholder names

### 3. Keep Scope Manageable

- **Size limit:** ~15 nodes or ~20 transitions per diagram
- **Split large diagrams:** If exceeding size limit, split into overarching diagram (architecture) + detailed diagram (state machine)
- **Example:** "Multi-Node Architecture" (7 nodes) separate from "Node Registry Lifecycle" (10 nodes)

### 4. Add Contextual Notes

- Use Mermaid notes to clarify less-obvious transitions (e.g., "MAX_FRAME_AGE_SECONDS threshold triggers staleness")
- Add surrounding markdown paragraphs explaining the diagram's purpose and key insights
- Document assumptions and future extensions

### 5. Test and Validate Rendering

- **Test syntax:** Copy diagram code into [mermaid.live](https://mermaid.live) and verify it renders without errors
- **Test GitHub rendering:** Verify diagram displays correctly on GitHub web (and mobile if possible)
- **Verify readability:** Can the intended audience (developer or operator) quickly understand the diagram?

### Reference: motion-in-ocean Terminology

| Concept | Definition | Context |
| --- | --- | --- |
| **`RECORDING` state** | Camera initialized and capturing frames; `recording_started` event set | State machine, health/readiness |
| **`STALE` frames** | Latest frame age exceeds `MAX_FRAME_AGE_SECONDS` (default: 10s) | Frame freshness, readiness |
| **`/health` endpoint** | Always returns HTTP 200; liveness probe; used by Docker healthcheck | Health/readiness state machine |
| **`/ready` endpoint** | Returns 200 only if camera is `RECORDING` AND frames not `STALE`; else 503 | Frame buffer, readiness logic |
| **`/stream.mjpg`** | MJPEG multipart stream; returns 503 if not ready | Frame pipeline, streaming |
| **Frame buffer lifecycle** | Picamera2 → JpegEncoder → FrameBuffer (sync) → MJPEG stream + snapshot | Pipeline diagram |
| **Bearer Token Auth** | Modern auth for node registry; replaces legacy basic auth | Node registry, API security |
| **FileNodeRegistry** | Persistent node storage (JSON file); CRUD at `/api/nodes` | Node registry, state |
| **Management mode** | Hub-and-spoke architecture; probes remote webcam hosts via HTTP | Architecture, deployment |
| **Webcam mode** | Runs on camera host; exposes `/stream.mjpg`, `/health`, `/ready`, `/metrics` | Architecture |
| **HTTP probe** | Management sends GET to remote `/health`, `/ready`, `/metrics` endpoint | API workflows |
| **Status aggregation** | Management consolidates node responses into `/api/management/overview` | API workflows |

## Validation checklist

- [ ] Diagram type chosen correctly for the concept (state machine for states, sequence for interactions, flowchart for architecture)
- [ ] All labels and terminology match [PRD-backend.md](../../PRD-backend.md), [PRD-frontend.md](../../PRD-frontend.md), codebase
- [ ] Mermaid syntax validates without errors at [mermaid.live](https://mermaid.live)
- [ ] Diagram renders correctly on GitHub web and mobile views
- [ ] Diagram scope ≤ ~15 nodes; if larger, split into multiple diagrams
- [ ] No ambiguous labels; all labels are explicit and specific
- [ ] Node IDs are deterministic (no random suffixes or placeholders)
- [ ] Contextual notes or surrounding markdown explain purpose and key insights
- [ ] Diagram is understandable to both developers and operators (where applicable)
- [ ] Assumptions and future extensions documented (if applicable)

## Source of truth

- [PRD-backend.md](../../PRD-backend.md) — Backend concepts, state machines, API workflows
- [PRD-frontend.md](../../PRD-frontend.md) — Frontend flows and interactions
- [DEPLOYMENT.md](../../docs/guides/DEPLOYMENT.md) — Architecture and deployment patterns
- [README.md](../../README.md) — Project overview and key terminology
- [pi_camera_in_docker/](../../pi_camera_in_docker/) — Actual implementation for terminology validation
- [Mermaid documentation](https://mermaid.js.org/) — Syntax and diagram types
- [mermaid.live](https://mermaid.live) — Online editor for testing syntax and rendering

## Common failure modes and recovery actions

| Failure | Cause | Recovery |
| --- | --- | --- |
| Diagram doesn't parse (syntax error) | Mermaid syntax mistake (typos, missing quotes, wrong node ID format) | Paste code into [mermaid.live](https://mermaid.live); read error message; fix syntax |
| Diagram doesn't render on GitHub | Markdown code block not marked as `mermaid` or indentation wrong | Verify code block starts with ````mermaid`` (3+ backticks, explicit language) |
| Labels don't match PRD or codebase | Terminology divergence or stale diagram | Compare labels to [PRD-backend.md](../../PRD-backend.md) / [PRD-frontend.md](../../PRD-frontend.md) / `pi_camera_in_docker/*.py`; update labels |
| Diagram too complex (>15 nodes, hard to read) | Trying to represent too much in one diagram | Split into overarching + detailed diagrams; use multiple diagrams with cross-references |
| Ambiguous labels ("Check", "Ready?") | Vague language that doesn't clarify intent | Rewrite labels to be explicit: "Check frame freshness", "Is frame fresh?" |
| Wrong diagram type used | Forced content into wrong diagram type (e.g., flowchart for state machine) | Redraw using correct diagram type; state machines → `stateDiagram-v2`, workflows → `sequenceDiagram`, architecture → `graph TD` |
| Diagram doesn't clarify anything | Adds visual noise but not insight | Step back; what is the core concept? Simplify; add notes; consider if diagram is needed |
| Non-deterministic node IDs | Node IDs use timestamps/random values | Use stable, meaningful IDs; e.g., `RECORDING`, `frame_buffer`, not `state_123_abc` |

## Maintenance notes

- Review this skill quarterly; especially when PRD-backend.md, PRD-frontend.md, or DEPLOYMENT.md changes significantly
- Update terminology reference table if new concepts are introduced (new state machines, API endpoints, architecture patterns)
- Test all existing diagrams at [mermaid.live](https://mermaid.live) annually to ensure syntax stability across Mermaid versions
- Document any Mermaid version constraints or known rendering issues (if any emerge)

---

## Related Skills

- **Before this skill:** [`documentation-build-validation`](../documentation-build-validation/SKILL.md) — Ensure Sphinx builds correctly (includes Mermaid validation)
- **During design:** [`front-end-design`](../front-end-design/SKILL.md) — Design principles for UI clarity (applies to diagram aesthetics)
- **Documentation context:** [CONTRIBUTING.md](../../CONTRIBUTING.md#documentation) — Contributor workflow for documentation changes
- **After implementation:** [`documentation-build-validation`](../documentation-build-validation/SKILL.md) — Re-validate after committing diagrams

Example response / additional context:

- Link to related sections in PRDs.
- Reference implementation in codebase.

````

---

## Failure / Stop Conditions

1. **Stop if requirements are too ambiguous to model faithfully:**
   - Example: Cannot diagram a workflow without knowing the exact sequence of state transitions.
   - **Resolution:** Return to PRD authors/SMEs for clarification before attempting diagram.

2. **Stop if diagram semantics conflict with PRD terminology:**
   - Example: PRD says state is `RECORDING` but diagram shows `ACTIVE` or `RUNNING`.
   - **Resolution:** Revise diagram to use exact terminology from source text.

3. **Stop if Mermaid syntax limitations prevent accurate modeling:**
   - Example: Complex conditional logic too intricate for standard flowchart.
   - **Resolution:** Split into multiple diagrams or augment with detailed text description.

4. **Stop if diagram would exceed 20 nodes/transitions:**
   - **Resolution:** Split into focused sub-diagrams with cross-references.

---

## Workflow: Creating a Diagram

1. **Identify trigger:** Which concept, workflow, or state machine in the PRD needs visualization?
2. **Choose diagram type:** Refer to mandatory rules section (state machine vs. flowchart vs. sequence vs. data flow).
3. **Extract terminology:** Copy exact labels from PRDs and codebase (e.g., `/ready`, `MAX_FRAME_AGE_SECONDS`, `recording_started`).
4. **Draft nodes/edges:** Build the diagram structure; validate syntax at [mermaid.live](https://mermaid.live).
5. **Test rendering:** Paste into GitHub markdown preview; verify on mobile.
6. **Write rationale:** 2–4 sentence explanation of diagram type choice and key insights.
7. **Place in markdown:** Insert into appropriate section with caption and surrounding context.
8. **Validation:** Walk through checklist above before committing.

---

## Example PRD Section with Integrated Diagram

From [PRD-backend.md](../../PRD-backend.md) section "Health & Readiness Probes (P1)":

---

### 2. Health & Readiness Probes (P1)

**Endpoints:**

- `GET /health` → Always returns 200 with `{ status: "healthy" }` and timestamp.
- `GET /ready` → Returns 200 when the camera has started recording **and** the latest frame age is within the configured threshold; otherwise returns 503 with reason and diagnostic fields.

**Readiness details:**

- Must indicate `not_ready` status when:
  - Camera recording is not started.
  - No frames have been captured yet.
  - Latest frame age exceeds `MAX_FRAME_AGE_SECONDS`.

**State transitions:**

```mermaid
stateDiagram-v2
    [*] --> STOPPED
    STOPPED --> INITIALIZING: camera_init()
    INITIALIZING --> RECORDING: recording_started.set()
    RECORDING --> STALE: frame age > MAX_FRAME_AGE_SECONDS
    STALE --> RECORDING: new frame captured
    RECORDING --> STOPPED: shutdown()
    STALE --> STOPPED: shutdown()
    STOPPED --> [*]

    note right of STOPPED
        /health: 200 ✓
        /ready: 503 (not ready)
    end note

    note right of INITIALIZING
        /health: 200 ✓
        /ready: 503 (not recording)
    end note

    note right of RECORDING
        /health: 200 ✓
        /ready: 200 ✓ (frames fresh)
    end note

    note right of STALE
        /health: 200 ✓
        /ready: 503 (frames stale)
    end note
````

**Figure 1: Health and Readiness State Transitions**

The state machine clarifies that `/health` is a liveness probe (always 200) while `/ready` is a readiness probe that transitions between 200 and 503 based on camera recording state and frame freshness (MAX_FRAME_AGE_SECONDS threshold). Operators can use this to understand why `/ready` might return 503 even when the service is healthy, indicating transient unavailability (e.g., camera initializing or frames stale due to network delays).

---

## Related Documentation

- [PRD-backend.md](../../PRD-backend.md) — Backend requirements, health/readiness specs.
- [PRD-frontend.md](../../PRD-frontend.md) — Frontend requirements, UI resilience and retry logic.
- [DEPLOYMENT.md](../../DEPLOYMENT.md) — Multi-host architecture, HTTP scenarios.
- [README.md](../../README.md) — Quick start, architecture overview, architecture & key concepts.
- [CONTRIBUTING.md](../../CONTRIBUTING.md) — Contribution guidelines, documentation standards.

---

## Tool & Resources

- **Mermaid Live Editor:** [mermaid.live](https://mermaid.live) (for syntax validation and quick testing)
- **Mermaid Documentation:** [mermaid.js.org](https://mermaid.js.org)
- **GitHub Mermaid Support:** [GitHub Markdown Mermaid Support](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams)
