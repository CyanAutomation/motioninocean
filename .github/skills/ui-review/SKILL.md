---
name: ui-review
description: Review visible motion-in-ocean interface changes for layout, content, accessibility, and interaction quality. Use after changing the streaming viewer, settings, or management dashboard.
owner: motion-in-ocean team
last-reviewed: 2026-09-25
category: Design
compatible-repo-areas:
  - frontend/src/
  - pi_camera_in_docker/templates/
  - pi_camera_in_docker/static/
  - docs/product/PRD-frontend.md
---

## Purpose

Catch visual and interaction regressions in the running interface with a repeatable manual review.

## Scope and trigger conditions

- Use for changes to the streaming viewer, settings, navigation, or management dashboard.
- Use [`frontend-testing-linting`](../frontend-testing-linting/SKILL.md) for frontend logic and unit tests.
- This review complements automated unit tests; it does not replace them.

## Required inputs

- A running webcam or management mode with representative data.
- The change description and the relevant screen or interaction.
- Desktop and narrow viewport sizes relevant to the change.

## Step-by-step workflow

1. Start the relevant mode using the setup described in `README.md` or `containers/README.md`.
2. Open the changed screen and check its initial, loading, empty, success, and error states where applicable.
3. Inspect at a desktop viewport and at a narrow mobile viewport. Check that content remains visible without horizontal overflow or overlap.
4. Navigate with the keyboard. Verify focus is visible, controls have useful names, and interaction does not depend on pointer input alone.
5. Check text contrast, control size, hierarchy, and consistency with the existing camera/operations interface.
6. Check the browser console for new errors and verify the visible data matches the relevant API response.
7. Record the screen, viewport, state, and any remaining issue in the pull request. Attach screenshots when they clarify the review.

## Validation checklist

- [ ] Relevant screen loads in the intended application mode.
- [ ] Desktop and narrow layouts keep controls and content readable and reachable.
- [ ] Loading, empty, success, and failure states are understandable.
- [ ] Keyboard focus and interaction work.
- [ ] Labels, contrast, and control feedback are clear.
- [ ] No new console errors or mismatches with API data appear.
- [ ] Automated frontend tests also pass when frontend logic changed.

## Source of truth

- `docs/product/PRD-frontend.md` — Product behavior and frontend requirements.
- `pi_camera_in_docker/templates/` and `pi_camera_in_docker/static/` — Current rendered UI.
- `frontend/src/` — Frontend logic and components.
- `tests/frontend/` — Automated frontend behavior checks.
- `docs/guides/DEPLOYMENT.md` — Modes, ports, and authentication boundaries.

## Common failure modes and recovery actions

- **Failure:** The management screen has no registered nodes. **Recovery:** Use an existing representative registry or record that populated-state review could not be completed.
- **Failure:** A state cannot be reached in the UI. **Recovery:** Use the documented API/runtime setup to reproduce it; do not infer behavior from a static screenshot.
- **Failure:** A desktop layout hides problems on a phone. **Recovery:** Recheck a narrow viewport and ensure navigation and content do not occupy the same space.
- **Failure:** A visual defect is reported without enough detail. **Recovery:** Include the screen, mode, viewport, steps, and a screenshot.

## Related Skills

- [`frontend-testing-linting`](../frontend-testing-linting/SKILL.md) — Test, lint, type-check, and build frontend code.
- [`front-end-design`](../front-end-design/SKILL.md) — Apply visual design and accessibility principles.
- [`deployment-validation-health-checks`](../deployment-validation-health-checks/SKILL.md) — Confirm the running mode and endpoints.

## Maintenance notes

Update this skill when the UI structure, application modes, or supported interaction patterns change.
