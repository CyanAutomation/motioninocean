---
name: mermaid-creator
description: Create or update Mermaid diagrams that explain motion-in-ocean architecture, state, or workflows. Use when a diagram makes product or operational behavior easier to understand.
owner: motion-in-ocean team
last-reviewed: 2026-09-25
category: Documentation
compatible-repo-areas:
  - docs/product/
  - docs/guides/
  - README.md
  - Makefile
---

## Purpose

Use diagrams to clarify project behavior without contradicting the implementation or product requirements.

## Scope and trigger conditions

- Use for architecture, API sequence, lifecycle, or deployment diagrams.
- Prefer a short text explanation when a diagram would only repeat it.
- Use [`documentation-build-validation`](../documentation-build-validation/SKILL.md) for build and syntax checks.

## Required inputs

- The behavior being explained and its audience.
- The authoritative code or requirement that defines it.
- The document where the diagram belongs.

## Step-by-step workflow

1. Read the relevant source in `pi_camera_in_docker/`, `docs/product/`, or `docs/guides/` before drawing the flow.
2. Choose a Mermaid type that matches the relationship: `flowchart` for branching or architecture, `sequenceDiagram` for interactions, and `stateDiagram-v2` for state transitions.
3. Use stable node IDs and labels that match the code and API. Keep one diagram focused; split it if the audience must trace unrelated flows at once.
4. Add a sentence before or after the diagram that explains its purpose and any assumptions.
5. Run `make validate-diagrams`. The target extracts and validates Mermaid fences in both product PRDs and the deployment guide.
6. Review the rendered diagram at the document’s actual destination and update nearby prose if the behavior changed.

## Validation checklist

- [ ] Diagram type matches the relationship being described.
- [ ] Nodes, endpoints, and transitions match implementation or requirements.
- [ ] Labels are specific and node IDs are stable.
- [ ] Supporting text explains the diagram’s scope.
- [ ] `make validate-diagrams` passes for a covered file.
- [ ] Rendered output is legible at the intended document width.

## Source of truth

- `docs/product/PRD-backend.md` — Backend and API requirements.
- `docs/product/PRD-frontend.md` — Frontend behavior.
- `docs/guides/DEPLOYMENT.md` — Deployment architecture and authentication.
- `README.md` — Project overview.
- `pi_camera_in_docker/` — Implemented runtime behavior.
- `Makefile` — Mermaid validation inputs and command.

## Common failure modes and recovery actions

- **Failure:** The diagram does not render. **Recovery:** Check Mermaid syntax and rerun `make validate-diagrams`.
- **Failure:** Labels disagree with the API or runtime. **Recovery:** Verify against implementation and update the diagram and nearby prose together.
- **Failure:** A diagram becomes difficult to scan. **Recovery:** Reduce detail or split independent flows into separate diagrams.
- **Failure:** A diagram file is not covered by the Make target. **Recovery:** Validate it with the installed Mermaid CLI and consider adding it to the target when it is a maintained project source.

## Related Skills

- [`documentation-build-validation`](../documentation-build-validation/SKILL.md) — Validate documentation output.
- [`contributor-workflow`](../contributor-workflow/SKILL.md) — Plan and review documentation changes.
- [`front-end-design`](../front-end-design/SKILL.md) — Apply information hierarchy to interface diagrams.

## Maintenance notes

Update the list of source files and validation inputs when PRDs, deployment docs, or the Makefile target move.
