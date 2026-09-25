---
name: documentation-build-validation
description: Build and validate Sphinx documentation, optional JSDoc output, and Mermaid diagrams. Use when changing docs, API docstrings, or diagrams.
owner: motion-in-ocean team
last-reviewed: 2026-09-25
category: Documentation
compatible-repo-areas:
  - docs/
  - pi_camera_in_docker/
  - frontend/src/
  - Makefile
---

## Purpose

Catch broken references, build errors, and invalid diagrams before documentation changes are merged.

## Scope and trigger conditions

- Use after changing Sphinx pages, Python docstrings, frontend documentation, or diagrams.
- `make docs-check` validates the Sphinx build. Diagram validation is a separate `make validate-diagrams` target.
- The current CI workflow does not run Sphinx, JSDoc, or Mermaid validation automatically.

## Required inputs

- The changed documentation/source files and their owning product or API behavior.
- Python development dependencies for Sphinx checks.
- Mermaid CLI on `PATH` for diagram validation.

## Step-by-step workflow

1. Build and validate Python documentation:

   ```bash
   make docs-check
   ```

   This runs Sphinx with warnings treated as errors and writes output under `docs/_build/html`.
2. If the change affects generated JSDoc, run `make jsdoc`. If JSDoc is unavailable, the target installs it as a development dependency; inspect any resulting package manifest changes before committing.
3. For Mermaid changes in either product PRD or the deployment guide, run:

   ```bash
   make validate-diagrams
   ```

   The target extracts individual Mermaid fences from `docs/product/PRD-backend.md`, `docs/product/PRD-frontend.md`, and `docs/guides/DEPLOYMENT.md`, then validates each with Mermaid CLI.
4. Inspect the changed rendered pages or diagram output and fix warnings or broken links at their source.
5. Run the relevant documentation and skill-link checks before finishing.

## Validation checklist

- [ ] `make docs-check` passes for Sphinx documentation changes.
- [ ] `make jsdoc` passes when generated API docs are part of the change.
- [ ] `make validate-diagrams` passes when diagrams change.
- [ ] Internal references point to the current document locations.
- [ ] Documentation describes current behavior and commands.

## Source of truth

- `Makefile` — Documentation and diagram validation targets.
- `docs/conf.py` — Sphinx configuration.
- `docs/index.rst` — Sphinx entry point.
- `jsdoc.json` — JSDoc source selection and output configuration.
- `docs/product/` and `docs/guides/` — Product requirements and operational documentation.
- `.github/workflows/ci.yml` — CI checks; currently no documentation build job is defined.

## Common failure modes and recovery actions

- **Failure:** Sphinx reports an undefined reference. **Recovery:** Update the target or reference path and rerun `make docs-check`.
- **Failure:** Mermaid reports a parse error. **Recovery:** Run the target again after simplifying the diagram syntax and inspect the failing input.
- **Failure:** Mermaid CLI is missing. **Recovery:** Install it in the local development environment; do not mistake missing tooling for a passing validation.
- **Failure:** JSDoc target changes package files. **Recovery:** Keep dependency changes only when intended and review the lockfile diff.

## Related Skills

- [`mermaid-creator`](../mermaid-creator/SKILL.md) — Create a project-accurate diagram.
- [`contributor-workflow`](../contributor-workflow/SKILL.md) — Plan and validate a documentation change.
- [`ci-quality-gates`](../ci-quality-gates/SKILL.md) — Run code and test gates.

## Maintenance notes

Review this skill when documentation targets, source locations, or CI coverage change.
