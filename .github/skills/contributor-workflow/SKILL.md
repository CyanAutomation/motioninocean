---
name: contributor-workflow
description: Execute standard motion-in-ocean contribution work from issue understanding to PR-ready validation. Use for code changes, documentation updates, bug fixes, and feature additions that must follow CONTRIBUTING.md and README.md guidance.
---

## Scope and trigger conditions

- Apply when implementing any change intended for a pull request.
- Apply when modifying runtime behavior, configuration, documentation, or scripts.
- Apply when changes should align with contributor expectations and local validation commands.

## Required inputs

- Change objective (bug fix, feature, docs update, or refactor).
- Files or components expected to change.
- Execution environment constraints (Pi vs non-Pi, mock camera usage).
- Target validation depth (quick checks vs full CI parity).

## Step-by-step workflow

1. Confirm task boundaries and identify impacted areas.
2. Review `README.md` sections related to runtime assumptions, configuration, and local development.
3. Review `CONTRIBUTING.md` for coding workflow, expected commands, and PR expectations.
4. Implement the smallest coherent change set.
5. If behavior/config changed, update documentation in `README.md` (or adjacent docs) to keep user guidance accurate.
6. Run baseline quality checks:
   - `make format`
   - `make lint`
   - `make type-check`
   - `make test` (or `make ci` when time permits)
7. Validate app behavior on non-Pi environments with `MOCK_CAMERA=true` if camera hardware is unavailable.
8. Prepare final change summary with what changed, why, and how it was tested.

## Validation checklist

- [ ] Changes are focused and consistent with existing style.
- [ ] Relevant docs were updated when behavior/configuration changed.
- [ ] Lint/format/type-check/tests were run successfully (or failures explained).
- [ ] Commands and examples remain compatible with current project tooling.
- [ ] Final summary includes explicit testing evidence.

## Common failure modes and recovery actions

- **Failure:** Code change passes locally but lacks docs updates.
  - **Recovery:** Re-open `README.md`/`CONTRIBUTING.md` sections and patch guidance immediately.
- **Failure:** Non-Pi development blocks camera-dependent validation.
  - **Recovery:** Enable `MOCK_CAMERA=true`, validate `/health` and `/ready`, and document limitation.
- **Failure:** PR scope grows too large.
  - **Recovery:** Split into smaller commits/PRs and keep each change independently testable.
- **Failure:** Checks are skipped due to time pressure.
  - **Recovery:** Run `make ci` before handoff and record any unavoidable exceptions.
