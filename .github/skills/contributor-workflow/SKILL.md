---
name: contributor-workflow
description: Plan, implement, and validate a focused motion-in-ocean change. Use when starting a feature, bug fix, refactor, or documentation update.
owner: motion-in-ocean team
last-reviewed: 2026-09-25
category: Development
compatible-repo-areas:
  - pi_camera_in_docker/
  - frontend/src/
  - tests/
  - docs/
---

## Purpose

Guide a change from a clear problem statement through a reviewable implementation and evidence-based validation.

## Scope and trigger conditions

- Use before changing application code, tests, deployment files, or documentation.
- Use [`ci-triage`](../ci-triage/SKILL.md) when diagnosing a specific failed workflow.
- Use [`release-operator`](../release-operator/SKILL.md) for versioned releases.

## Required inputs

- Desired behavior, affected mode or user, and known constraints.
- Relevant source files and existing tests.
- Required runtime or hardware context, if the change depends on it.

## Step-by-step workflow

1. Inspect the working tree and the relevant implementation, tests, and source documentation.
2. State the intended behavior and identify observable acceptance checks.
3. For a behavior change, write or update a focused regression test first and run it to confirm it fails for the expected reason.
4. Make the smallest implementation that satisfies the failing test. Keep configuration, API contracts, and documentation aligned.
5. Rerun the focused test, then the relevant project checks. For a full local gate set, run `make validate`.
6. Review the final diff for unrelated changes, secrets, generated artifacts, and incomplete docs.
7. Summarize what changed, why, the checks run, and any unverified hardware or deployment behavior.

## Validation checklist

- [ ] Change matches the stated behavior and project architecture.
- [ ] Behavior changes have a focused regression test where practical.
- [ ] Relevant Python, frontend, or documentation checks pass.
- [ ] API/configuration/documentation changes agree with their source of truth.
- [ ] Final diff contains only intended files and no secrets.

## Source of truth

- `AGENTS.md` — Architecture and repository conventions.
- `CONTRIBUTING.md` — Contribution and review expectations.
- `Makefile` and `.github/workflows/ci.yml` — Validation commands and CI checks.
- `pi_camera_in_docker/` and `frontend/src/` — Runtime implementation.
- `tests/` — Existing behavior contracts and regression coverage.

## Common failure modes and recovery actions

- **Failure:** Test setup depends on Raspberry Pi hardware. **Recovery:** Use the mock camera for host-side checks and report hardware-specific checks as unverified.
- **Failure:** A test passes before the fix. **Recovery:** Recheck the test’s setup and assertion; ensure it reproduces the reported behavior.
- **Failure:** A docs build fails on an unrelated missing optional tool. **Recovery:** Report the exact missing tool and run link/structure checks available locally.
- **Failure:** A generated file changes unexpectedly. **Recovery:** Check its generator and CI parity step before committing it.

## Related Skills

- [`ci-quality-gates`](../ci-quality-gates/SKILL.md) — Run repository validation.
- [`frontend-testing-linting`](../frontend-testing-linting/SKILL.md) — Validate TypeScript and JavaScript changes.
- [`ui-review`](../ui-review/SKILL.md) — Review visible interface changes.
- [`documentation-build-validation`](../documentation-build-validation/SKILL.md) — Validate Sphinx docs and Mermaid diagrams.

## Maintenance notes

Review this skill when the contribution process, project architecture, or validation commands change.
