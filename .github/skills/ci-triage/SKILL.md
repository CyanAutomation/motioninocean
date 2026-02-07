---
name: ci-triage
description: Job-by-job triage playbooks for CI and security workflows, including local reproduction, pass criteria, and escalation guidance.
---

## Purpose

Use this skill when a GitHub Actions failure needs fast diagnosis in:

- `.github/workflows/ci.yml` jobs: `test`, `lint`, `type-check`, `security`
- `.github/workflows/security-scan.yml` job: `scan` (Trivy)

## Global triage sequence (all jobs)

1. Confirm failing workflow/job name and read the first failing step log.
2. Reproduce with the **Makefile target first** for speed, then run the matching direct CI command for parity.
3. Inspect the first implicated file(s), fix root cause, rerun only the failing job commands.
4. Run broader validation (`make ci` or targeted workflow-equivalent command set) before closing triage.
5. Escalate when findings indicate infra/secrets/policy/tooling-version issues outside normal code fixes.

---

## Job playbook: `ci.yml` → `test`

### Typical failure signatures

- `FAILED tests/...::...` assertion errors.
- `ModuleNotFoundError` / import failures.
- `fixture '...' not found` or pytest config errors.
- Coverage invocation issues from `--cov=pi_camera_in_docker`.
- Version-sensitive failures in matrix (`3.9`, `3.11`, `3.12`) that do not reproduce on one interpreter.

### First files to inspect

- Changed test files under `tests/`.
- Changed runtime code under `pi_camera_in_docker/` touched by the failing tests.
- `pyproject.toml` for pytest/coverage options.
- `requirements-dev.txt` when dependency/import errors appear.

### Fast local reproduction

- Make target:
  - `make test`
- CI-parity direct command:
  - `pytest tests/ --cov=pi_camera_in_docker --cov-report=term-missing --cov-report=xml --cov-report=html -v`
- Matrix-focused repro (if available):
  - `python3.9 -m pytest tests/ -v`
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

## Suggested closure template for triage notes

- **Job:** `<workflow>/<job>`
- **Failure signature:** `<first key error>`
- **Local repro command(s):** `<make ...>` / `<direct ...>`
- **Root cause:** `<one-line cause>`
- **Resolution:** `<fix applied or decision>`
- **Escalation:** `<none | owner/ticket>`
