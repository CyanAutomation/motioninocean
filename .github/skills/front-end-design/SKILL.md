---
name: front-end-design
description: Design and refine motion-in-ocean’s camera and operations interfaces. Use when changing layout, visual hierarchy, controls, or interface states.
owner: motion-in-ocean team
last-reviewed: 2026-09-25
category: Design
compatible-repo-areas:
  - frontend/src/
  - pi_camera_in_docker/templates/
  - pi_camera_in_docker/static/css/
  - docs/product/PRD-frontend.md
---

## Purpose

Keep the camera viewer and operations dashboard clear, reliable, and accessible while they present live status and controls.

## Scope and trigger conditions

- Use when designing or changing an existing screen, navigation, form, or status presentation.
- Use [`ui-review`](../ui-review/SKILL.md) to inspect the running result.
- Follow `docs/product/PRD-frontend.md` for product behavior; do not introduce an unrelated marketing layout.

## Required inputs

- Screen, user task, and application mode (webcam or management).
- Relevant status/API data and existing design patterns.
- Supported desktop and mobile viewport expectations.

## Step-by-step workflow

1. Identify the user’s primary task and the information needed to complete it.
2. Inspect the existing templates, styles, frontend source, and product requirements before adding a new pattern.
3. Give live status, stream availability, and important actions clear visual priority. Keep secondary diagnostics easy to find without crowding the main task.
4. Use consistent spacing, type, color, and component behavior from the existing interface. Use imagery only when it helps a camera or operational task.
5. Design loading, empty, error, disabled, and success states alongside the default state.
6. Preserve semantic controls, visible keyboard focus, readable contrast, responsive reflow, and reduced-motion preferences.
7. Review the running screen with [`ui-review`](../ui-review/SKILL.md), then run `make test-frontend` and relevant checks.

## Validation checklist

- [ ] The visual hierarchy follows the user’s primary task.
- [ ] Status and controls remain understandable at narrow widths.
- [ ] Interactive elements have clear names, focus, and feedback.
- [ ] Color is not the only way to distinguish status.
- [ ] Error and unavailable states are designed, not left blank.
- [ ] The final result is consistent with the product requirements and adjacent screens.

## Source of truth

- `docs/product/PRD-frontend.md` — Frontend requirements and expected behavior.
- `frontend/src/` — Current frontend structure and design tokens.
- `pi_camera_in_docker/templates/` — Flask-rendered page structure.
- `pi_camera_in_docker/static/css/` — Existing styles and responsive rules.
- `docs/guides/DEPLOYMENT.md` — Webcam and management modes.

## Common failure modes and recovery actions

- **Failure:** A screen looks polished but hides the stream or a critical status. **Recovery:** Reorder content around the operator’s primary task and validate against actual status data.
- **Failure:** Desktop-specific layout overflows on mobile. **Recovery:** Reflow content and test a narrow viewport rather than shrinking every element.
- **Failure:** Status relies on color alone. **Recovery:** Add text or an icon with an accessible name.
- **Failure:** New controls lack keyboard feedback. **Recovery:** Use semantic controls and restore visible focus styles.

## Related Skills

- [`ui-review`](../ui-review/SKILL.md) — Review the running interface.
- [`frontend-testing-linting`](../frontend-testing-linting/SKILL.md) — Validate frontend source and generated assets.
- [`contributor-workflow`](../contributor-workflow/SKILL.md) — Plan and implement the change.

## Maintenance notes

Review this skill when the product interface, visual tokens, accessibility standards, or frontend architecture changes.
