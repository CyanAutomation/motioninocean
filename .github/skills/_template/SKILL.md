---
name: <skill-name>
description: <one-to-two sentence summary of what this skill does and when to apply it>
owner: <team-or-individual>
last-reviewed: YYYY-MM-DD
compatible-repo-areas:
  - <path-or-area-1>
  - <path-or-area-2>
---

## Purpose

Describe the business/engineering goal and expected outcome.

## Scope and trigger conditions

- List concrete situations that should trigger use of this skill.
- List explicit out-of-scope cases.

## Required inputs

- Enumerate the minimum context and artifacts needed before execution.

## Step-by-step workflow

1. Provide an ordered, actionable sequence.
2. Prefer deterministic commands and file paths over vague guidance.
3. Call out decision points and fallback paths.

## Validation checklist

- [ ] Define objective pass/fail checks tied to repository workflows.
- [ ] Include at least one check that verifies docs/process alignment.

## Source of truth

List the repository files that govern this skill's behavior. Include specific paths/globs and why they matter.

- `.github/workflows/*.yml` — CI, release, and automation behavior.
- `README.md` — canonical setup and usage guidance.
- `CONTRIBUTING.md` — contribution and quality expectations.

## Common failure modes and recovery actions

- **Failure:** <what commonly goes wrong>
  - **Recovery:** <how to recover safely>

## Maintenance notes

- Review and refresh this skill at least quarterly and whenever source-of-truth files change.
- Update `last-reviewed` whenever any section is modified.

## Writing standards

- Use imperative voice and concise, testable instructions.
- Reference exact file paths, commands, and environment variables.
- Avoid speculation; if assumptions are required, state them explicitly.
- Keep sections scannable with short bullets and numbered steps.
- Ensure guidance is reproducible by a contributor unfamiliar with the area.
