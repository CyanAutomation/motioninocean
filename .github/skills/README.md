# Project Skills Index

This directory contains reusable execution playbooks for common motion-in-ocean tasks.

| Skill | Purpose | Use when... |
|---|---|---|
| [`contributor-workflow`](./contributor-workflow/SKILL.md) | Plan, implement, and validate day-to-day code or docs changes using project contribution standards. | You are adding/fixing functionality, updating docs, or preparing a PR that must satisfy local quality gates. |
| [`ci-quality-gates`](./ci-quality-gates/SKILL.md) | Run and interpret CI-equivalent checks (tests, lint, type checks, security) before pushing changes. | You need confidence that changes will pass `.github/workflows/ci.yml` and `security-scan.yml`. |
| [`release-operator`](./release-operator/SKILL.md) | Execute and verify the automated, tag-driven release process with rollback awareness. | You are cutting a release, validating release prerequisites, or troubleshooting release automation. |

## Source references used

- `README.md` for quick start, local development, and CI/CD expectations.
- `CONTRIBUTING.md` for contributor workflow and validation commands.
- `.github/workflows/*.yml` for exact CI and release automation behavior.
- `CHANGELOG.md` for release note structure and version history conventions.
- `RELEASE.md` for tag-driven release process and rollback mechanics.
