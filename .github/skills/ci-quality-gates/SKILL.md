---
name: ci-quality-gates
description: Reproduce and evaluate motion-in-ocean CI and security quality gates locally. Use when validating pull requests, diagnosing CI failures, or ensuring parity with workflows in .github/workflows/ci.yml and security-scan.yml.
---

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

## Common failure modes and recovery actions

- **Failure:** Local commands differ from workflow tooling versions.
  - **Recovery:** Align versions with workflow setup (Python 3.11 baseline for lint/type/security).
- **Failure:** Tests pass locally but fail in matrix versions.
  - **Recovery:** Re-run tests on additional Python versions (3.9/3.11/3.12) or use matrix-compatible environment.
- **Failure:** Security checks produce noisy/non-blocking findings.
  - **Recovery:** Triage critical/high issues first, annotate accepted risks, and open follow-up issues.
- **Failure:** Docker-based scans cannot run due environment constraints.
  - **Recovery:** Run available static checks, report limitation, and defer full scan to CI with clear note.
