---
name: documentation-build-validation
description: Build, validate, and troubleshoot Sphinx HTML documentation, JSDoc generation, and Mermaid diagram syntax for motion-in-ocean project documentation.
owner: motion-in-ocean team
last-reviewed: 2026-08-05
category: Documentation
compatible-repo-areas:
  - docs/
  - pi_camera_in_docker/static/js/
  - jsdoc.json
  - pyproject.toml
  - Makefile
  - .github/workflows/ci.yml
---

## Purpose

Enable developers to build, validate, and troubleshoot project documentation before pushing changes. Motion-in-ocean uses three documentation systems: Sphinx (Python API docs), JSDoc (JavaScript API docs), and Mermaid (architecture/workflow diagrams). This skill ensures all documentation builds successfully locally and matches CI validation expectations.

## Scope and trigger conditions

Apply this skill when:

- Building HTML documentation locally before submitting changes to `docs/` or docstrings
- Debugging `docs-check` failures in GitHub Actions CI
- Adding or updating Python docstrings (Google-style format)
- Adding or updating JavaScript JSDoc comments
- Creating or updating Mermaid diagrams in documentation files
- Validating diagram syntax after editing architecture or workflow diagrams

Do NOT use this skill for:

- Editing documentation content alone (without building/validating)
- Troubleshooting non-documentation build issues (Python app, Docker image, etc.)
- Writing documentation content (use this skill only for validation/building)

## Required inputs

- Python 3.10+ with development dependencies installed (`make install-dev`)
- Node.js 18+ (for JSDoc generation)
- Clean checkout of documentation files
- Text editor for reviewing generated HTML output (optional, but helpful)

## Step-by-step workflow

### Build Sphinx (Python API) documentation

1. Ensure Python dev dependencies are installed:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. Build HTML documentation:
   ```bash
   make docs-build
   ```

3. View generated docs:
   ```bash
   # Open in browser (Linux/macOS)
   open docs/_build/html/index.html
   # Or on any OS
   python -m http.server -d docs/_build/html 8888
   # Then visit http://localhost:8888
   ```

4. Verify all Python modules are documented:
   - Check that `docs/_build/html/modules.html` lists all modules in `pi_camera_in_docker/`
   - Ensure no "WARNING: autodoc: failed to import module" messages in build output

### Validate Python docstrings (pre-build check)

1. Verify all public functions/classes have Google-style docstrings:
   ```bash
   # Search for undocumented public functions (optional manual check)
   grep -rn "^def " pi_camera_in_docker/*.py | grep -v "^.*:.*def _"
   ```

2. Ensure docstrings follow the required format:
   - One-line summary
   - Detailed description (if needed)
   - Args section: parameter names, types, descriptions
   - Returns section: type and description
   - Raises section (if applicable): exception types
   - Examples or Notes for complex logic

### Build JSDoc (JavaScript API) documentation

1. Ensure Node.js dependencies are installed:
   ```bash
   npm install
   ```

2. Generate JSDoc documentation:
   ```bash
   make jsdoc
   ```

3. View generated docs:
   ```bash
   # Open in browser
   open docs/_build/html/js/index.html
   ```

4. Verify all JavaScript modules are documented:
   - Check `docs/_build/html/js/index.html` for completeness
   - Ensure functions, classes, and methods have JSDoc headers

### Validate Mermaid diagram syntax

1. Check Mermaid diagram validity in documentation:
   ```bash
   make validate-diagrams
   ```

2. If validation fails, the output will show line numbers and syntax errors

3. Common Mermaid issues:
   - Mismatched brackets or quotes
   - Invalid keywords (e.g., typos in `graph TD`, `sequenceDiagram`)
   - Incorrect arrow syntax
   - Missing semicolons in some diagram types

4. Test individual diagrams by copying them to [mermaid.live](https://mermaid.live) for interactive debugging

### Run full documentation check (CI equivalent)

1. Run the comprehensive CI check:
   ```bash
   make docs-check
   ```

2. This runs:
   - Sphinx build with warnings-as-errors (`-W` flag)
   - JSDoc generation
   - Mermaid diagram validation

3. Address any errors before commit

## Related Skills

- **Mermaid diagrams:** Use [`mermaid-creator`](../mermaid-creator/SKILL.md) to create/validate diagrams before build
- **Docstring writing:** Reference [AGENTS.md#documentation-requirements](../../AGENTS.md#documentation-requirements) for style
- **Before PR:** Run this skill to validate docs won't fail CI

## Validation checklist

- [ ] `make docs-build` completes without errors or warnings
- [ ] `make jsdoc` completes and generates `docs/_build/html/js/index.html`
- [ ] `make validate-diagrams` passes all Mermaid syntax checks
- [ ] `make docs-check` passes (CI equivalent)
- [ ] All docstrings follow Google-style format (Args, Returns, Raises sections)
- [ ] All JavaScript functions have JSDoc headers with @param, @returns, @async tags
- [ ] No broken internal documentation links (verify in generated HTML)
- [ ] Mermaid diagrams render correctly in `docs/` markdown files

## Source of truth

- `Makefile` — `docs-build`, `docs-check`, `jsdoc`, `validate-diagrams` targets
- `pyproject.toml` — Sphinx configuration (extensions, theme, build options)
- `docs/conf.py` — Detailed Sphinx configuration
- `jsdoc.json` — JSDoc generation configuration
- `docs/` directory structure — Documentation files, guides, and architecture diagrams
- `.github/workflows/ci.yml` — CI documentation validation job (`docs-check` step)

## Common failure modes and recovery actions

| Failure | Cause | Recovery |
|---------|-------|----------|
| `ModuleNotFoundError` during Sphinx build | Missing Python dependencies | Run `pip install -r requirements-dev.txt` and retry `make docs-build` |
| `autodoc: failed to import module <name>` | Module not properly installed or import error in module | Check that module can be imported: `python -c "import pi_camera_in_docker.<name>"` |
| `WARNING: undefined label` in Sphinx build | Broken internal link in documentation | Search docs/ for the undefined label reference and fix the link |
| JSDoc generation produces empty output | Node.js dependencies not installed | Run `npm install` and retry `make jsdoc` |
| Mermaid diagram fails validation | Syntax error in diagram definition | Copy diagram to [mermaid.live](https://mermaid.live), debug interactively, fix syntax |
| `make docs-check` fails but `docs-build` passes | Sphinx warnings treated as errors in CI | Review warning output and fix issues (e.g., missing docstring sections, broken links) |

## Maintenance notes

- Review and refresh this skill **whenever documentation tooling changes** (Sphinx version, JSDoc config, Mermaid validation rules)
- Update `last-reviewed` when changes are made to:
  - Sphinx configuration (`pyproject.toml`, `docs/conf.py`)
  - JSDoc generation (`jsdoc.json`)
  - CI documentation job (`.github/workflows/ci.yml`)
  - Docstring or JSDoc standards (`CONTRIBUTING.md`, this skill)

## Writing standards

- Use imperative voice in workflow steps (e.g., "Build HTML documentation" not "Building...")
- Include exact make target names and command-line examples
- Reference specific file paths (e.g., `docs/_build/html/index.html` not "the build output directory")
- Document both successful paths and common failure recovery
- Keep validation checklist tied to concrete verification steps
