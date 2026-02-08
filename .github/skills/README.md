# Project Skills Index

This directory contains reusable execution playbooks for common motion-in-ocean tasks.

| Skill                                                     | Purpose                                                                                             | Use when...                                                                                                  |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| [`contributor-workflow`](./contributor-workflow/SKILL.md) | Plan, implement, and validate day-to-day code or docs changes using project contribution standards. | You are adding/fixing functionality, updating docs, or preparing a PR that must satisfy local quality gates. |
| [`ci-quality-gates`](./ci-quality-gates/SKILL.md)         | Run and interpret CI-equivalent checks (tests, lint, type checks, security) before pushing changes. | You need confidence that changes will pass `.github/workflows/ci.yml` and `security-scan.yml`.               |
| [`release-operator`](./release-operator/SKILL.md)         | Execute and verify the automated, tag-driven release process with rollback awareness.               | You are cutting a release, validating release prerequisites, or troubleshooting release automation.          |

## Skill authoring template

Use [`_template/SKILL.md`](./_template/SKILL.md) when creating or updating a skill.

## Maintenance policy

### Required metadata (frontmatter)

Every skill must include these metadata fields:

- `name`
- `description`
- `owner`
- `last-reviewed` (ISO date, `YYYY-MM-DD`)
- `compatible-repo-areas` (list of paths/components the skill applies to)

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
