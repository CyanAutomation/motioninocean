---
name: frontend-testing-linting
description: Build, test, lint, type-check, and format the project’s TypeScript and JavaScript. Use for changes under frontend/, tests/frontend/, or generated frontend assets.
owner: motion-in-ocean team
last-reviewed: 2026-09-25
category: Development
compatible-repo-areas:
  - frontend/
  - tests/frontend/
  - pi_camera_in_docker/static/js/
  - package.json
  - tsconfig.json
---

## Purpose

Validate frontend source changes using the scripts and test runner configured in this repository.

## Scope and trigger conditions

- Use when editing TypeScript, JavaScript, frontend tests, or generated frontend assets.
- Use [`ui-review`](../ui-review/SKILL.md) for visual and interaction review of the running interface.
- Do not invent npm scripts: use only those listed in `package.json`.

## Required inputs

- Node.js 20, npm, and the changed source/test files.
- A clear expected behavior for any frontend logic change.

## Step-by-step workflow

1. Install the locked dependencies when needed:

   ```bash
   npm ci
   ```

2. For a behavior change, add or update a focused test in `tests/frontend/` and run it to confirm the expected failure.
3. Run frontend tests and build:

   ```bash
   make test-frontend
   ```

   This runs `npm run build:frontend` and `node --test tests/frontend/*.test.mjs`.
4. Run static checks:

   ```bash
   npm run lint
   npm run type-check
   npm run format:check
   ```

5. If a TypeScript change updates generated files under `pi_camera_in_docker/static/js`, review and commit the intended output. CI checks regeneration with `git diff --exit-code -- pi_camera_in_docker/static/js`.
6. Review the rendered behavior and keyboard interaction using [`ui-review`](../ui-review/SKILL.md).

## Validation checklist

- [ ] Focused test fails before and passes after a behavior fix.
- [ ] `make test-frontend` passes.
- [ ] `npm run lint`, `npm run type-check`, and `npm run format:check` pass.
- [ ] Generated assets are current and intentional.
- [ ] Visible changes have been reviewed at relevant viewport sizes and with keyboard input.

## Source of truth

- `package.json` — Supported npm scripts and frontend tool dependencies.
- `tsconfig.json` — TypeScript source and compiler settings.
- `.github/workflows/ci.yml` — Node version, frontend test command, and generated-file check.
- `frontend/src/` — TypeScript source modules.
- `tests/frontend/` — Node built-in test cases.
- `pi_camera_in_docker/static/js/` — Generated browser assets served by Flask.

## Common failure modes and recovery actions

- **Failure:** `make test-frontend` cannot find a test file. **Recovery:** Check `tests/frontend/*.test.mjs` and confirm the test was added to the repository.
- **Failure:** Generated JavaScript differs after build. **Recovery:** Inspect the TypeScript changes and generated diff; rebuild with `npm run build:frontend`.
- **Failure:** An npm command is unknown. **Recovery:** Check `package.json`; the supported scripts are `build:frontend`, `lint`, `type-check`, `format`, and `format:check`.
- **Failure:** Lint fixes cause broad unrelated edits. **Recovery:** Format only the intended files with the repository tool and inspect the diff.

## Related Skills

- [`contributor-workflow`](../contributor-workflow/SKILL.md) — Plan and implement the change.
- [`ci-quality-gates`](../ci-quality-gates/SKILL.md) — Run broader local checks.
- [`ui-review`](../ui-review/SKILL.md) — Review visible interface behavior.
- [`front-end-design`](../front-end-design/SKILL.md) — Apply project design principles.

## Maintenance notes

Update this skill when `package.json`, TypeScript configuration, generated asset paths, frontend tests, or the corresponding CI job changes.
