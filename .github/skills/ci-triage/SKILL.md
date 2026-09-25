---
name: ci-triage
description: Diagnose a failed GitHub Actions check, reproduce it locally, and identify the smallest reliable fix. Use when a CI or image-security job fails.
owner: motion-in-ocean team
last-reviewed: 2026-09-25
category: CI/CD
compatible-repo-areas:
  - .github/workflows/ci.yml
  - .github/workflows/security-scan.yml
  - tests/
  - Makefile
---

## Purpose

Turn a CI failure into a reproducible cause, a focused fix, and a passing rerun of the affected checks.

## Scope and trigger conditions

- Use when a job in `.github/workflows/ci.yml` or `.github/workflows/security-scan.yml` fails.
- Use [`ci-quality-gates`](../ci-quality-gates/SKILL.md) for pre-push validation.
- This skill covers diagnosis; workflow policy changes need a reviewed change to the workflow files.

## Required inputs

- Workflow run, job name, failed step, and the first relevant error from its log.
- Branch or commit that CI checked.
- Python, Node.js, Docker, or GitHub access required by the failed job.

## Step-by-step workflow

1. Read the full failed step and identify the earliest actionable error.
2. Match the job to the table below and run its local command from the repository root.
3. Inspect the files named in the error and compare tool versions/configuration with the workflow.
4. Make the smallest fix. For behavior changes, add or update a regression test before fixing the failure.
5. Rerun the failing command, then run `make validate` for broader local coverage.
6. Report the root cause, changed files, and exact validation results. Escalate runner, secret, or permissions issues to a maintainer.

| CI job | Local reproduction | Notes |
| --- | --- | --- |
| `frontend-tests` | `make test-frontend` | Builds TypeScript and runs `node --test tests/frontend/*.test.mjs`. |
| `test` | `python -m pytest tests/ -v` | CI tests Python 3.10, 3.11, and 3.12. |
| `runtime-dependency-resolution` | Repeat the `pip download` step in `.github/workflows/ci.yml` with the same interpreter/platform. | The matrix checks default and optional runtime requirements on x86_64 and aarch64. |
| `lint` | `make lint`, `npm run type-check`, `npm run build:frontend`, `python -m ruff format --check .`, `python -m pi_camera_in_docker.feature_flag_usage_check` | CI also verifies generated frontend files stay unchanged. |
| `type-check` | `make type-check` | A mypy failure is blocking. |
| `security` | `make security` | Runs Bandit. |
| `scan` | Build the image, then run Trivy as configured in `.github/workflows/security-scan.yml`. | Reports all severities; fixed HIGH and CRITICAL findings block. |
| `upload-sarif` | Inspect the preceding `scan` output and artifact. | Runs only for default-branch pushes or manual runs on that branch, with security-events permission. |
| `arm64-smoke` | `docker buildx build --platform linux/arm64 --build-arg INCLUDE_MOCK_CAMERA=true --load --tag motion-in-ocean:arm64-smoke .` | Requires Docker Buildx and ARM emulation support. |

## Validation checklist

- [ ] Failed workflow, job, and step are identified.
- [ ] Earliest actionable error is captured.
- [ ] A local reproduction or a clear runner/environment limitation is recorded.
- [ ] The fix has a regression test when it changes behavior.
- [ ] The failed check passes after the fix.
- [ ] Broader validation is run or its limits are stated.

## Source of truth

- `.github/workflows/ci.yml` — CI job names, matrices, commands, and versions.
- `.github/workflows/security-scan.yml` — Trivy, SARIF, and ARM64 jobs.
- `Makefile` — Local equivalents such as `make test-frontend`, `make type-check`, and `make security`.
- `package.json` — Supported frontend scripts.
- `pyproject.toml` — Python tooling configuration.

## Common failure modes and recovery actions

- **Failure:** It passes locally but fails in CI. **Recovery:** Match the CI interpreter, Node version, platform, and environment variables.
- **Failure:** A security report step fails after the scan. **Recovery:** Check whether scan output exists and whether the run is eligible for report publication before treating it as a vulnerability finding.
- **Failure:** A dependency only fails in the architecture matrix. **Recovery:** Reproduce the exact interpreter/platform combination and inspect wheel availability and optional requirements.
- **Failure:** Authentication or runner permissions block a step. **Recovery:** Preserve the log and ask a repository maintainer to inspect repository settings; do not work around permissions by exposing secrets.

## Related Skills

- [`ci-quality-gates`](../ci-quality-gates/SKILL.md) — Run the local gate set before pushing.
- [`contributor-workflow`](../contributor-workflow/SKILL.md) — Implement and validate the underlying change.
- [`frontend-testing-linting`](../frontend-testing-linting/SKILL.md) — Diagnose frontend test or tooling failures.

## Maintenance notes

Keep the job table synchronized with the two workflow files. Review it whenever a job, matrix, or validation command changes.
