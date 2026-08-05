---
name: ci-quality-gates
description: Reproduce and evaluate motion-in-ocean CI and security quality gates locally. Use when validating pull requests, diagnosing CI failures, or ensuring parity with workflows in .github/workflows/ci.yml and security-scan.yml.
owner: motion-in-ocean team
last-reviewed: 2026-08-05
category: CI/CD
compatible-repo-areas:
  - .github/workflows/ci.yml
  - .github/workflows/security-scan.yml
  - Makefile
  - requirements-dev.txt
  - pyproject.toml
---

## Purpose

Enable developers to validate their changes against motion-in-ocean's CI quality gates locally before pushing to GitHub. This skill ensures code meets the project's standards for testing, linting, type safety, and security scanning. Local validation reduces CI failures and accelerates feedback cycles.

## Scope and trigger conditions

- Apply before opening/merging PRs.
- Apply when CI failures need reproduction or root-cause analysis.
- Apply when dependency or infrastructure changes might affect tests, linting, typing, or security scans.

## Required inputs

- Current branch and diff under test.
- Availability of Python tooling and Docker in local environment.
- Whether full parity is required or a targeted subset is acceptable.

## Step-by-step workflow

1. Inspect `.github/workflows/ci.yml` to map required checks:
   - tests with coverage
   - Ruff lint + formatting check
   - mypy (currently non-blocking in workflow)
   - Bandit and Safety checks
2. Inspect `.github/workflows/security-scan.yml` for Docker/Trivy scan expectations.
3. Install/update development dependencies (`requirements-dev.txt`) and tooling.
4. Run project command shortcuts from `CONTRIBUTING.md` where possible:
   - `make lint`
   - `make type-check`
   - `make test`
   - `make ci`
5. For CI parity checks, run direct commands matching workflow behavior as needed (e.g., `ruff check .`, `ruff format --check .`, `pytest ... --cov ...`).
6. If container-level risks are relevant, build image and run local security scan equivalents.
7. Record outputs and classify results as pass, expected warning, or fail.

## Validation checklist

- [ ] Local checks cover all relevant CI jobs for the change.
- [ ] Any divergence from workflow behavior is explicitly documented.
- [ ] Failures include reproducible command output and root-cause notes.
- [ ] Security-relevant changes receive at least baseline scanning.
- [ ] Final status clearly indicates merge readiness.

## Related Skills

- **Before this step:** [`contributor-workflow`](../contributor-workflow/SKILL.md) — Plan and implement your change first
- **If CI still fails:** [`ci-triage`](../ci-triage/SKILL.md) — Diagnose specific job failures in detail
- **Frontend specific:** [`frontend-testing-linting`](../frontend-testing-linting/SKILL.md) — Run JS/TS quality checks
- **Before release:** [`release-operator`](../release-operator/SKILL.md) — Run full quality gates before release

## Common failure modes and recovery actions

- **Failure:** Local commands differ from workflow tooling versions.
  - **Recovery:** Align versions with workflow setup (Python 3.11 baseline for lint/type/security).
- **Failure:** Tests pass locally but fail in matrix versions.
  - **Recovery:** Re-run tests on additional Python versions (3.10/3.11/3.12) or use matrix-compatible environment.
- **Failure:** Security checks produce noisy/non-blocking findings.
  - **Recovery:** Triage critical/high issues first, annotate accepted risks, and open follow-up issues.
- **Failure:** Docker-based scans cannot run due environment constraints.
  - **Recovery:** Run available static checks, report limitation, and defer full scan to CI with clear note.

## Source of truth

- `.github/workflows/ci.yml` — Exact CI job definitions, tooling versions, and validation order (test, lint, type-check, security)
- `.github/workflows/security-scan.yml` — Docker image security scanning with Trivy
- `Makefile` — Local CI equivalent commands (`make ci`, `make test`, `make lint`, `make type-check`, `make security`)
- `requirements-dev.txt` — Python dev dependencies and versions for CI tooling (pytest, ruff, mypy, bandit)
- `pyproject.toml` — Project metadata, pytest configuration, coverage settings
- `CONTRIBUTING.md` — Contributor expectations and CI validation process

## Maintenance notes

- Review this skill quarterly and immediately when `.github/workflows/ci.yml` or `Makefile` changes
- Update `last-reviewed` field on every review
- Test that local Makefile targets produce equivalent results to GitHub Actions jobs (especially after CI workflow updates)
