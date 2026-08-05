# Project Skills Index

This directory contains reusable execution playbooks for common motion-in-ocean tasks.

## Skills by Category

### CI/CD

| Skill | Purpose | Last Reviewed |
| ------- | --------- | --------------- |
| [`ci-quality-gates`](./ci-quality-gates/SKILL.md) | Reproduce and evaluate CI/security gates locally before pushing changes. | 2026-08-05 |
| [`ci-triage`](./ci-triage/SKILL.md) | Diagnose CI job failures with playbooks for test, lint, type-check, security, and scan jobs. | 2026-08-05 |
| [`release-operator`](./release-operator/SKILL.md) | Execute tag-driven releases with preflight checks, verification, and rollback awareness. | 2026-08-05 |
| [`release-publish`](./release-publish/SKILL.md) | Run and verify Docker/GitHub Release publication via `.github/workflows/docker-publish.yml`. | 2026-08-05 |
| [`nightly-autofix-workflow`](./nightly-autofix-workflow/SKILL.md) | Monitor and troubleshoot scheduled nightly code quality automation (ESLint, Ruff, Prettier). | 2026-08-05 |
| [`dependabot-dependency-management`](./dependabot-dependency-management/SKILL.md) | Review, test, and merge Dependabot PRs for Python and JavaScript/TypeScript dependencies. | 2026-08-05 |

### Development

| Skill | Purpose | Last Reviewed |
| ------- | --------- | --------------- |
| [`contributor-workflow`](./contributor-workflow/SKILL.md) | Plan, implement, and validate code/docs changes with quality gate validation. | 2026-08-05 |
| [`frontend-testing-linting`](./frontend-testing-linting/SKILL.md) | Run Node.js tests, ESLint, and Prettier for JavaScript/TypeScript; includes fallow integration for code health assessment. | 2026-08-05 |
| [`feature-flag-management`](./feature-flag-management/SKILL.md) | Enable, disable, and test feature flags; understand flag lifecycle for development and production. | 2026-08-05 |

### Deployment

| Skill | Purpose | Last Reviewed |
|-------|---------|---------------|
| [`pi-camera-troubleshooting`](./pi-camera-troubleshooting/SKILL.md) | Diagnose camera startup, streaming, device mapping, and health check failures. | 2026-08-05 |
| [`deployment-validation-health-checks`](./deployment-validation-health-checks/SKILL.md) | Validate post-deployment container health, device mapping, and API endpoint availability. | 2026-08-05 |

### Design

| Skill | Purpose | Last Reviewed |
|-------|---------|---------------|
| [`ui-playwright`](./ui-playwright/SKILL.md) | Audit motion-in-ocean web UI (streaming viewer, node management) with Playwright. | 2026-08-05 |
| [`front-end-design`](./front-end-design/SKILL.md) | Create visually strong UIs with restrained composition, image-led hierarchy, and tasteful motion. | 2026-08-05 |

### Documentation

| Skill | Purpose | Last Reviewed |
|-------|---------|---------------|
| [`mermaid-creator`](./mermaid-creator/SKILL.md) | Create clear, semantically meaningful Mermaid diagrams for architecture, workflows, and PRDs. | 2026-08-05 |
| [`documentation-build-validation`](./documentation-build-validation/SKILL.md) | Build, validate, and troubleshoot Sphinx documentation, JSDoc generation, and Mermaid diagrams. | 2026-08-05 |

## Skill authoring template

Use [`_template/SKILL.md`](./_template/SKILL.md) when creating or updating a skill.

## Maintenance policy

### Required metadata (frontmatter)

Every skill must include these metadata fields:

- `name` (required)
- `description` (required)
- `owner` (required)
- `last-reviewed` (required, ISO date format `YYYY-MM-DD`)
- `category` (recommended; one of: CI/CD, Development, Deployment, Documentation, Design, Tools)
- `compatible-repo-areas` (required, list of paths/components the skill applies to)

### Required content sections

Every skill must include all of the following sections:

- `## Purpose`
- `## Scope and trigger conditions`
- `## Required inputs`
- `## Step-by-step workflow`
- `## Validation checklist`
- `## Source of truth`
- `## Common failure modes and recovery actions`
- `## Maintenance notes`
- `## Writing standards`

The `## Source of truth` section is mandatory and must reference specific repository files (not generic statements). At minimum, include:

- `.github/workflows/*.yml`
- `README.md`
- `CONTRIBUTING.md`

Add additional files as needed for the skill domain (for example `RELEASE.md`, `CHANGELOG.md`, deployment config, or service-specific docs).

### Review cadence

Review each skill:

- At least **quarterly**, and
- Immediately when related workflows, documentation, or operating procedures change.

Update the `last-reviewed` field on every review and whenever substantive edits are made.

### Change triggers requiring skill updates

Update affected skills when any of the following change:

- CI/release/automation workflow files under `.github/workflows/`
- Release process definitions (for example `RELEASE.md`, versioning, tagging, or publish mechanics)
- Configuration or environment behavior (new/changed env vars, runtime defaults, deployment settings)
- Contributor process documentation (`README.md`, `CONTRIBUTING.md`, quality gates, or PR expectations)

## Source references used

- `README.md` for quick start, local development, and CI/CD expectations.
- `CONTRIBUTING.md` for contributor workflow and validation commands.
- `.github/workflows/*.yml` for exact CI and release automation behavior.
- `CHANGELOG.md` for release note structure and version history conventions.
- `RELEASE.md` for tag-driven release process and rollback mechanics.
