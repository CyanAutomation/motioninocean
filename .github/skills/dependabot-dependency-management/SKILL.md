---
name: dependabot-dependency-management
description: Review Dependabot pull requests against the actual update policy and CI results. Use for GitHub Actions, npm, or pip dependency updates.
owner: motion-in-ocean team
last-reviewed: 2026-09-25
category: CI/CD
compatible-repo-areas:
  - .github/dependabot.yml
  - requirements.txt
  - requirements-dev.txt
  - package.json
  - package-lock.json
  - .github/workflows/ci.yml
---

## Purpose

Evaluate dependency updates for compatibility, security, and build impact before merging.

## Scope and trigger conditions

- Use for Dependabot pull requests or changes to `.github/dependabot.yml`.
- The repository currently configures GitHub Actions, npm, and pip updates on a weekly schedule. It does not configure Docker image updates.
- Use [`ci-triage`](../ci-triage/SKILL.md) to investigate a failed check.

## Required inputs

- Pull request description and changed manifests/lockfiles.
- CI results and dependency release notes for changes that may be breaking.
- Local Python and Node.js environments when reproducing a failure.

## Step-by-step workflow

1. Read `.github/dependabot.yml` and confirm the ecosystem, grouping, schedule, and any ignore rules.
2. Review the full pull request diff. Confirm it changes the expected manifest or lockfile and does not contain unrelated application edits.
3. Check release notes and compatibility constraints, especially for major versions. TypeScript major updates are explicitly ignored until handled as a migration.
4. Wait for required CI checks. For local reproduction, install from the lockfiles and run:

   ```bash
   npm ci
   make test-frontend
   npm run lint
   npm run type-check
   make validate
   ```

   Run only the relevant subset when the update affects a single ecosystem, and state what was skipped.
5. Merge only when required checks pass and the change is understood. For failing or breaking updates, document the evidence and follow-up needed; do not merge solely because the update is routine or security-related.
6. After merge, inspect the default-branch checks for regressions.

## Validation checklist

- [ ] Ecosystem and changed dependencies match the configured update.
- [ ] Manifest and lockfile changes are expected and consistent.
- [ ] Required CI checks pass.
- [ ] Major-version or security impact has been reviewed from authoritative release/advisory details.
- [ ] Merge, defer, or close decision is supported by the observed evidence.

## Source of truth

- `.github/dependabot.yml` — Enabled ecosystems, schedule, grouping, and ignore rules.
- `.github/workflows/ci.yml` — Dependency and application validation.
- `requirements.txt` and `requirements-dev.txt` — Python dependency declarations.
- `package.json` and `package-lock.json` — Node dependency declarations and lockfile.
- `Dockerfile` — Container base image and OS package sources; no automated image update is configured.

## Common failure modes and recovery actions

- **Failure:** Lockfile and manifest disagree. **Recovery:** Regenerate using the repository’s package manager and inspect the resulting diff.
- **Failure:** A major update breaks type-checking or tests. **Recovery:** Read the migration guide, make any required source changes in a focused pull request, or defer the update.
- **Failure:** CI fails only on one Python version or architecture. **Recovery:** Reproduce the exact matrix entry and check package support for that platform.
- **Failure:** A vulnerability fix causes a regression. **Recovery:** Assess exploitability and available compatible versions, then coordinate a tested remediation; do not suppress the failing check without review.

## Related Skills

- [`ci-quality-gates`](../ci-quality-gates/SKILL.md) — Run local validation.
- [`ci-triage`](../ci-triage/SKILL.md) — Diagnose dependency-related check failures.
- [`release-operator`](../release-operator/SKILL.md) — Prepare a release after merged updates.

## Maintenance notes

Update this skill when ecosystems, schedules, grouping, ignore rules, or dependency validation in CI change.
