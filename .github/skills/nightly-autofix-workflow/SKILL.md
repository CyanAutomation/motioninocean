---
name: nightly-autofix-workflow
description: Understand and review the scheduled code-quality autofix workflow. Use when its run fails or it opens an automated pull request.
owner: motion-in-ocean team
last-reviewed: 2026-09-25
category: CI/CD
compatible-repo-areas:
  - .github/workflows/linting-autofix.yml
  - eslint.config.js
  - pyproject.toml
  - package.json
  - Makefile
---

## Purpose

Explain how scheduled formatting changes are produced and how to review them safely.

## Scope and trigger conditions

- Use when the scheduled code-quality workflow fails or creates a pull request.
- The workflow runs daily at 03:00 UTC and can also be started manually. Its job runs only for the repository’s default branch.
- It opens or updates a pull request on `autofix/nightly`; auto-merge is disabled.

## Required inputs

- Workflow run or pull request URL.
- Access to the changed files and the required CI results.
- Repository access if local reproduction is needed.

## Step-by-step workflow

1. Read `.github/workflows/linting-autofix.yml` and inspect the first failing step in the Actions log.
2. For a failure, reproduce the corresponding Ruff, ESLint, Prettier, or `make ci` command locally.
3. For an opened pull request, inspect all changed files and confirm the diff is limited to expected fixes and formatting.
4. Check that the pull request’s required CI checks pass. Review semantic changes manually; formatting automation does not establish behavioral correctness.
5. Merge only through the repository’s normal review rules. The workflow does not merge its own pull requests.
6. If changes are incorrect, fix the source rule or code in a reviewed change; do not repeatedly fight the generated diff.

## Validation checklist

- [ ] Workflow file and failure log were reviewed.
- [ ] Pull request changes are expected and contain no unrelated edits.
- [ ] Required CI checks pass.
- [ ] Any non-formatting behavior change received human review.
- [ ] Merge decision follows repository review policy.

## Source of truth

- `.github/workflows/linting-autofix.yml` — Schedule, tools, branch, and pull request behavior.
- `eslint.config.js` — ESLint rules.
- `pyproject.toml` — Ruff configuration.
- `package.json` — Frontend tools and supported npm scripts.
- `Makefile` — CI validation command used after autofixes.

## Common failure modes and recovery actions

- **Failure:** Workflow installation fails. **Recovery:** Check npm lockfile and Python requirements resolution in the logs.
- **Failure:** The formatting step creates broad changes. **Recovery:** Identify the changed rule or tool version and review a narrower formatter diff.
- **Failure:** A generated pull request has failing checks. **Recovery:** Reproduce the failing check and fix the cause before merging.
- **Failure:** No pull request is created. **Recovery:** Check the job summary for “No changes detected” and confirm the workflow ran on the default branch.

## Related Skills

- [`ci-quality-gates`](../ci-quality-gates/SKILL.md) — Run the same local checks.
- [`ci-triage`](../ci-triage/SKILL.md) — Diagnose Actions failures.
- [`contributor-workflow`](../contributor-workflow/SKILL.md) — Make a reviewed code-quality change.

## Maintenance notes

Update this skill when the workflow schedule, tools, target branch, or pull request behavior changes.
