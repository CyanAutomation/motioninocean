---
name: ci-quality-gates
description: Run the repository’s local lint, type, test, and security checks. Use before opening a pull request or when checking whether a change is ready for CI.
owner: motion-in-ocean team
last-reviewed: 2026-09-25
category: CI/CD
compatible-repo-areas:
  - .github/workflows/ci.yml
  - .github/workflows/security-scan.yml
  - Makefile
  - requirements-dev.txt
  - pyproject.toml
---

## Purpose

Run the same relevant checks contributors and CI use, and report any checks that could not run locally.

## Scope and trigger conditions

- Use before opening or merging a pull request, or when CI parity is needed.
- Use [`ci-triage`](../ci-triage/SKILL.md) to investigate a specific failed job.
- This skill covers local validation; it does not authorize merging or releasing.

## Required inputs

- The branch and changes to validate.
- Python and Node.js environments listed in `README.md` and `.github/workflows/ci.yml`.
- Docker and Trivy only when checking the image scan locally.

## Step-by-step workflow

1. Read `.github/workflows/ci.yml` and identify checks that touch the changed files. The workflow runs frontend tests, Python tests across 3.10–3.12, dependency resolution, lint/format checks, mypy, and Bandit.
2. Install the repository dependencies with `pip install -r requirements-dev.txt` and `npm ci` when needed.
3. Run the full local Makefile validation:

   ```bash
   make validate
   ```

   `make ci` runs lint, format check, type check, feature-flag usage validation, and tests. `make validate` adds Bandit through `make security`.
4. For frontend-only changes, run `make test-frontend`, `npm run lint`, and `npm run type-check`. CI also checks that `npm run build:frontend` leaves generated files under `pi_camera_in_docker/static/js` unchanged.
5. For container changes, inspect `.github/workflows/security-scan.yml`. It builds an image, reports all Trivy severities, blocks fixed HIGH and CRITICAL findings, publishes SARIF on default-branch pushes, and smoke-tests an ARM64 image.
6. Record the exact commands run and any local environment limitations.

## Validation checklist

- [ ] Relevant checks from `.github/workflows/ci.yml` pass.
- [ ] `make validate` passes, or each failure has a diagnosis.
- [ ] Generated frontend assets are current after TypeScript changes.
- [ ] Container changes are checked against the image scan policy.
- [ ] Local and CI differences are documented.

## Source of truth

- `.github/workflows/ci.yml` — CI jobs, Python/Node versions, and exact commands.
- `.github/workflows/security-scan.yml` — Image scanning, enforcement, SARIF, and ARM64 smoke test.
- `Makefile` — Local validation targets and which gates they include.
- `package.json` — Frontend scripts.
- `requirements-dev.txt` and `pyproject.toml` — Python tools and test configuration.

## Common failure modes and recovery actions

- **Failure:** `make ci` passes but Bandit has not run. **Recovery:** Run `make security` or `make validate`; Bandit is not included in `make ci`.
- **Failure:** Frontend tests fail after editing TypeScript. **Recovery:** Run `npm run build:frontend`, inspect generated JavaScript, then run `node --test tests/frontend/*.test.mjs`.
- **Failure:** A local command is missing. **Recovery:** Compare the command with `Makefile` or `package.json`; do not substitute an assumed script.
- **Failure:** Trivy is unavailable locally. **Recovery:** Record that limitation and use the required GitHub Actions result for the image scan.

## Related Skills

- [`contributor-workflow`](../contributor-workflow/SKILL.md) — Plan and implement a change.
- [`frontend-testing-linting`](../frontend-testing-linting/SKILL.md) — Frontend-specific validation.
- [`ci-triage`](../ci-triage/SKILL.md) — Investigate a failed CI job.
- [`release-operator`](../release-operator/SKILL.md) — Prepare a tagged release.

## Maintenance notes

Review this skill whenever the CI workflows, Makefile, package scripts, or Python tooling change. Update `last-reviewed` after verifying or editing it.
