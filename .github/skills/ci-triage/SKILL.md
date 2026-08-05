---
name: ci-triage
description: Job-by-job triage playbooks for CI and security workflows, including local reproduction, pass criteria, and escalation guidance.
owner: motion-in-ocean team
last-reviewed: 2026-08-05
category: CI/CD
compatible-repo-areas:
  - .github/workflows/ci.yml
  - .github/workflows/security-scan.yml
  - tests/
  - Makefile
---

## Purpose

Enable developers and operators to rapidly diagnose and fix GitHub Actions CI failures. This skill provides job-specific playbooks with typical failure signatures, reproduction steps, pass criteria, and escalation guidance. Following these playbooks reduces debugging time and ensures issues are fixed at the right layer (code, config, or infrastructure).

## Scope and trigger conditions

Apply this skill when:

- A GitHub Actions job fails in `.github/workflows/ci.yml` (test, lint, type-check, security) or `.github/workflows/security-scan.yml` (scan)
- CI failure blocks PR merge or indicates a regression
- Local reproduction is needed to diagnose root cause
- Unclear whether failure is code-level, dependency-level, or infrastructure-level

Do NOT use this skill for:

- Fixing code before running CI (use [`contributor-workflow`](../contributor-workflow/SKILL.md) first)
- Preventing CI failures in the first place (use [`ci-quality-gates`](../ci-quality-gates/SKILL.md) to validate locally before pushing)
- Modifying CI workflow configuration (that requires code review in a PR to `.github/workflows/`)

## Required inputs

- GitHub Actions job name and failing step (from GitHub UI or notification)
- Ability to run local Makefile targets and Python/Node.js commands
- Access to failing commit or branch for local reproduction
- Familiarity with project structure, test patterns, and linting rules
- Optional: `gh` CLI for querying workflow logs directly

## Step-by-step workflow

### Global triage sequence (all jobs)

1. Confirm failing workflow/job name and read the first failing step log.
2. Reproduce with the **Makefile target first** for speed, then run the matching direct CI command for parity.
3. Inspect the first implicated file(s), fix root cause, rerun only the failing job commands.
4. Run broader validation (`make ci` or targeted workflow-equivalent command set) before closing triage.
5. Escalate when findings indicate infra/secrets/policy/tooling-version issues outside normal code fixes.

Job-specific playbooks follow below, organized by job name.

## Validation checklist

- [ ] Failed job name and step clearly identified from GitHub Actions UI
- [ ] First failing step log read and searched for error keywords
- [ ] Local reproduction attempted with Makefile target or direct command
- [ ] Root cause identified and classified (code, dependency, config, or infra)
- [ ] If code fix: change made, job re-run locally, result documented
- [ ] If dependency: version checked, lockfile updated if needed
- [ ] If config: workflow or tool config reviewed, validation attempted
- [ ] If infra/policy: escalation decision made with reasoning documented
- [ ] Final validation run (`make ci` or equivalent) shows job passing
- [ ] PR comment or commit message documents diagnosis and fix

## Source of truth

- `.github/workflows/ci.yml` — Exact job definitions, steps, and commands that fail
- `.github/workflows/security-scan.yml` — Security scanning job configuration
- `Makefile` — Local equivalents for each CI job (make test, make lint, make type-check, make security)
- `requirements-dev.txt` — Python testing/linting tool versions (pytest, ruff, mypy, bandit)
- `package.json` — Node.js testing/linting tool versions (eslint, prettier)
- `pyproject.toml` — pytest and tool configuration (coverage, mypy flags)
- `CONTRIBUTING.md` — Contributor workflow and quality expectations

## Common failure modes and recovery actions

See job-specific playbooks below for detailed diagnosis. At a high level:

- **Failure:** Local reproduction succeeds but CI fails
  - **Recovery:** Check Python/Node version in CI workflow vs local; may be matrix-specific (e.g., Python 3.10 vs 3.11)
- **Failure:** Flaky tests pass/fail unpredictably
  - **Recovery:** Run 3 times locally to confirm reproducibility; if still flaky, open issue with details
- **Failure:** Dependency resolution fails only in CI
  - **Recovery:** Check lockfile versions; may need `pip install --upgrade` or `npm ci` regeneration
- **Failure:** Tool version drift causes different results locally vs CI
  - **Recovery:** Verify tool versions match workflow (e.g., `ruff --version`, `mypy --version`)
- **Failure:** Infra/secrets issue (e.g., missing GHCR auth, branch protection rule)
  - **Recovery:** Escalate to repo admin; document in GitHub issue; do not attempt local workarounds

## Maintenance notes

- Review this skill quarterly and immediately when `.github/workflows/ci.yml`, `.github/workflows/security-scan.yml`, or `Makefile` changes
- Update `last-reviewed` field whenever workflow or job definitions change significantly
- Ensure job playbooks below stay synchronized with actual workflow jobs (add new jobs when added to CI)
- Test local reproduction commands remain consistent with workflow commands

---

## Job playbooks by job type

### Job playbook: `ci.yml` → `test`

### Typical failure signatures

- `FAILED tests/...::...` assertion errors.
- `ModuleNotFoundError` / import failures.
- `fixture '...' not found` or pytest config errors.
- Coverage invocation issues from `--cov=pi_camera_in_docker`.
- Version-sensitive failures in matrix (`3.10`, `3.11`, `3.12`) that do not reproduce on one interpreter.

### First files to inspect

- Changed test files under `tests/`.
- Changed runtime code under `pi_camera_in_docker/` touched by the failing tests.
- `pyproject.toml` for pytest/coverage options.
- `requirements-dev.txt` when dependency/import errors appear.

### Fast local reproduction

- Make target:
  - `make test`
- CI-parity direct command:
  - `python -m pytest tests/ -v`
- Matrix-focused repro (if available):
  - `python3.10 -m pytest tests/ -v`
  - `python3.11 -m pytest tests/ -v`
  - `python3.12 -m pytest tests/ -v`

### Pass criteria

- Test command exits `0`.
- No unexpected test failures.
- Coverage command completes and writes reports (xml/html) without errors.
- For matrix-only failures: identified and fixed or documented with a compatibility follow-up.

### Escalate when

- Failures occur only in CI-hosted Python versions not available locally.
- Flake appears nondeterministic/retry-sensitive across reruns.
- Dependency resolution breaks across the full test matrix.

---

## Job playbook: `ci.yml` → `lint`

### Typical failure signatures

- Ruff rule violations (`F...`, `E...`, `B...`, etc.) in `ruff check` output.
- Import ordering/style findings from isort/ruff rules.
- `ruff format --check` reporting files would be reformatted.

### First files to inspect

- Files listed in Ruff output (first error first).
- `pyproject.toml` Ruff config sections.
- Any newly added modules/tests not conforming to formatting/rule set.

### Fast local reproduction

- Make targets:
  - `make lint`
  - `make format-check`
- CI-parity direct commands:
  - `ruff check . --output-format=github`
  - `ruff format --check .`
- Fast auto-fix (non-parity helper):
  - `make lint-fix`
  - `make format`

### Pass criteria

- `ruff check` exits `0`.
- `ruff format --check` exits `0` with no reformat-needed files.

### Escalate when

- Rule disagreements imply policy/config change rather than one-off fix.
- Tooling version drift between local and CI changes lint behavior unexpectedly.

---

## Job playbook: `ci.yml` → `type-check`

### Special policy note

- The `Run mypy` step in `.github/workflows/ci.yml` currently uses `continue-on-error: true`.
- This means mypy regressions are **non-blocking** today unless repository policy changes.
- Treat new type errors as important quality debt; prioritize fixes, but classify merge impact according to current policy.

### Typical failure signatures

- mypy errors such as:
  - `error: Incompatible types in assignment [assignment]`
  - `error: Argument ... has incompatible type ... [arg-type]`
  - `error: Item ... has no attribute ... [attr-defined]`
- Import typing noise when stubs are missing (despite `--ignore-missing-imports`).

### First files to inspect

- File/line shown by mypy output (first error first).
- Changed type annotations in `pi_camera_in_docker/`.
- `Makefile`/workflow mypy flags if behavior differs.

### Fast local reproduction

- Make target:
  - `make type-check`
- CI-parity direct command:
  - `mypy pi_camera_in_docker/ --ignore-missing-imports --show-error-codes`
- Relaxed local target currently includes additional permissive flags in Makefile; use direct command to match CI exactly.

### Pass criteria

- Preferred: mypy exits `0` with no errors.
- Current non-blocking policy: triage is acceptable if errors are understood, documented, and tracked for follow-up.

### Escalate when

- Type errors indicate runtime correctness risk in critical paths.
- Error volume spikes after dependency/type-stub upgrades.
- Team intends to remove `continue-on-error` or make type checks blocking.

---

## Job playbook: `ci.yml` → `security`

### Typical failure signatures

- Bandit findings with severity/confidence annotations in console output.
- `bandit-report.json` generation failures.
- Safety dependency vulnerability output from `safety check --json`.

### First files to inspect

- Reported source files in `pi_camera_in_docker/`.
- `pyproject.toml` `[tool.bandit]` config.
- Dependency manifests (`requirements*.txt`) for vulnerable package versions.

### Fast local reproduction

- Make targets:
  - `make security`
  - `make security-all`
- CI-parity direct commands:
  - `bandit -r pi_camera_in_docker/ -c pyproject.toml -f json -o bandit-report.json || true`
  - `bandit -r pi_camera_in_docker/ -c pyproject.toml`
  - `safety check --json || true`

### Pass criteria

- No unaccepted high-risk Bandit findings in modified code.
- Safety output reviewed; critical/high vulnerabilities have remediation or approved exception path.
- Security artifacts generate successfully when required.

### Escalate when

- Critical/high vulnerabilities lack immediate safe remediation.
- Findings suggest secrets exposure, unsafe deserialization, command injection, or auth flaws.
- Vulnerabilities originate in transitive dependencies requiring coordinated upgrades.

---

## Job playbook: `security-scan.yml` → `scan` (Trivy)

### Typical failure signatures

- Docker build fails (`docker build -t motion-in-ocean:scan .`).
- Trivy action fails to scan image or produce `trivy-results.sarif` / `trivy-report.json`.
- SARIF upload step errors (permissions/schema/artifact issues).
- High/critical CVEs discovered in OS/library packages.

### First files to inspect

- `Dockerfile` and any referenced build assets/scripts.
- Dependency manifests copied into image (`requirements*.txt`, apt/apk package instructions).
- `.github/workflows/security-scan.yml` for scan parameters (`severity`, `vuln-type`, outputs).

### Fast local reproduction

- Make target (build only):
  - `make docker-build`
- CI-parity direct commands:
  - `docker build -t motion-in-ocean:scan .`
  - `trivy image --severity CRITICAL,HIGH,MEDIUM --format table motion-in-ocean:scan`
  - `trivy image --severity CRITICAL,HIGH,MEDIUM --format sarif --output trivy-results.sarif motion-in-ocean:scan`
  - `trivy image --severity CRITICAL,HIGH --format json --output trivy-report.json motion-in-ocean:scan`

### Pass criteria

- Docker image builds successfully for scan target.
- Trivy completes and generates expected outputs.
- No untriaged critical/high vulnerabilities (or formally accepted exceptions with owners and due dates).

### Escalate when

- CVEs are critical/high and fixed versions are unavailable.
- Vulnerabilities are in base image layers requiring platform-wide image strategy changes.
- CI runner permission/tooling issues block SARIF upload or actionable reporting.

---

## Related Skills

- **Before this (prevent failures):** [`contributor-workflow`](../contributor-workflow/SKILL.md) — Follow contributor workflow to avoid CI failures
- **Reproduce locally:** [`ci-quality-gates`](../ci-quality-gates/SKILL.md) — Run local CI gate checks to reproduce failure
- **If frontend-specific:** [`frontend-testing-linting`](../frontend-testing-linting/SKILL.md) — Diagnose JS/TS test or lint failures
- **After diagnosis:** Use relevant skill per job type (see playbooks above)

---

## Suggested closure template for triage notes

- **Job:** `<workflow>/<job>`
- **Failure signature:** `<first key error>`
- **Local repro command(s):** `<make ...>` / `<direct ...>`
- **Root cause:** `<one-line cause>`
- **Resolution:** `<fix applied or decision>`
- **Escalation:** `<none | owner/ticket>`
