---
name: frontend-testing-linting
description: Run and debug Node.js unit tests, ESLint checks, and Prettier formatting for motion-in-ocean JavaScript/TypeScript frontend code; includes fallow integration for JavaScript/TypeScript health assessment.
owner: motion-in-ocean team
last-reviewed: 2026-08-05
category: Development
compatible-repo-areas:
  - pi_camera_in_docker/static/js/
  - pi_camera_in_docker/templates/
  - tests/ui/
  - package.json
  - eslint.config.js
  - playwright.ui.config.mjs
  - .github/workflows/ci.yml
  - .github/workflows/nightly-autofix.yml
---

## Purpose

Enable frontend developers to validate JavaScript/TypeScript code quality locally before pushing changes. Motion-in-ocean frontend validation includes unit tests (Playwright), linting (ESLint), code formatting (Prettier), and optional health assessment via fallow (for detailed JS/TS code quality insights). This skill ensures changes meet CI standards and maintains consistent code style across the frontend codebase.

## Scope and trigger conditions

Apply this skill when:

- Making changes to JavaScript files in `pi_camera_in_docker/static/js/`
- Adding or updating HTML templates in `pi_camera_in_docker/templates/`
- Debugging `frontend-tests` CI job failures
- Running ESLint or Prettier checks before commit
- Assessing JavaScript/TypeScript code quality and health using fallow (optional, manual invocation)
- Adding new npm dependencies or updating `package.json`

Do NOT use this skill for:

- Fixing Python code quality issues (use contributor-workflow skill)
- Performing comprehensive performance profiling (fallow is code quality, not performance)
- Automated test generation (fallow can suggest tests, but doesn't generate them automatically)
- Linting/formatting Python files

## Required inputs

- Node.js 18+ with npm installed
- `package.json` and `node_modules/` up to date (run `npm install`)
- ESLint and Prettier configurations present (`eslint.config.js`, `.prettierrc` or Prettier config in `package.json`)
- Playwright browser automation available (for UI tests)
- Optional: fallow CLI installed globally for health assessment (`npm install -g fallow` or `cargo install fallow` if building from source)

## Step-by-step workflow

### Install dependencies

1. Install Node.js dependencies:
   ```bash
   npm install
   ```

2. Verify Node.js version (18+):
   ```bash
   node --version
   ```

### Run ESLint (linting)

1. Check for linting violations:
   ```bash
   npm run lint
   ```

2. Review output for violations (errors and warnings)

3. Auto-fix fixable violations:
   ```bash
   npm run lint:fix
   # Or directly with ESLint
   npx eslint --fix pi_camera_in_docker/static/js/ pi_camera_in_docker/templates/
   ```

4. Common ESLint issues:
   - Unused variables (use `// eslint-disable-next-line` sparingly if needed)
   - Missing semicolons (Prettier will handle if semicolon rule is enabled)
   - Incorrect indentation (auto-fixed by Prettier)
   - Console statements in production code (should be removed or wrapped in debug guards)

### Run Prettier (code formatting)

1. Check formatting without changes:
   ```bash
   npm run format:check
   # Or directly with Prettier
   npx prettier --check pi_camera_in_docker/static/js/ pi_camera_in_docker/templates/
   ```

2. Auto-format all files:
   ```bash
   npm run format
   # Or directly with Prettier
   npx prettier --write pi_camera_in_docker/static/js/ pi_camera_in_docker/templates/
   ```

3. Note: Prettier may change whitespace and line breaks; this is expected

## Related Skills

- **Before committing:** [`contributor-workflow`](../contributor-workflow/SKILL.md) — Part of quality gate validation
- **UI testing:** [`ui-playwright`](../ui-playwright/SKILL.md) — Test JavaScript functionality with browser automation
- **Design review:** [`front-end-design`](../front-end-design/SKILL.md) — Ensure UI follows design principles
- **Feature flags in UI:** [`feature-flag-management`](../feature-flag-management/SKILL.md) — Gate new JS features
- **If tests fail:** [`testing-strategy`](../testing-strategy/SKILL.md) (coming soon) — Write or fix failing tests

### Run Unit Tests (Playwright)

1. Run all frontend tests:
   ```bash
   npm run test
   ```

2. Run tests in watch mode (re-run on file changes):
   ```bash
   npm run test:watch
   ```

3. Generate coverage report:
   ```bash
   npm run test:coverage
   ```

4. Review coverage output to identify untested code paths

5. Run a specific test file:
   ```bash
   npm run test -- <test-file-path>
   ```

### Validate type checking (TypeScript, if applicable)

1. Run TypeScript type checker (if configured):
   ```bash
   npm run type-check
   # Or directly
   npx tsc --noEmit
   ```

2. Address any type errors before proceeding

### Use fallow for JavaScript/TypeScript health assessment (Optional, Manual)

**What is fallow?** 

Fallow ([fallow-rs/fallow](https://github.com/fallow-rs/fallow)) is a static analyzer for JavaScript and TypeScript that provides detailed code health assessment including:
- Code complexity metrics (cyclomatic complexity, cognitive complexity)
- Dead code detection
- Test coverage analysis
- Security vulnerability suggestions
- Code maintainability scoring
- Duplicate code detection

**When to use fallow:**

- Assessing code health before major refactors
- Identifying complex functions that need simplification
- Finding dead code to clean up
- Understanding test coverage gaps
- Performance code review before optimization
- Detailed health report generation for documentation

**Installation:**

```bash
# Option 1: Install from npm (if available)
npm install -g fallow

# Option 2: Install from Rust source (recommended for latest features)
cargo install fallow
```

**Basic usage:**

```bash
# Analyze current directory
fallow

# Analyze specific file
fallow pi_camera_in_docker/static/js/app.js

# Generate detailed report
fallow --json > fallow-report.json

# Show only critical issues
fallow --level critical
```

**Reading fallow output:**

Fallow provides metrics and suggestions such as:

```
Cyclomatic Complexity: 8 (moderate)
Cognitive Complexity: 12 (high)
Dead Code: 2 functions
Duplicated Code: 3 blocks
Test Coverage: 72% (7 uncovered branches)
Maintainability Index: 65 (good)
```

**Integration with CI (optional, future):**

Fallow can be integrated into `.github/workflows/ci.yml` to enforce code health thresholds:

```bash
fallow --max-complexity 10 --min-coverage 80
```

**When NOT to use fallow:**

- For automated formatting (use Prettier)
- For simple linting (use ESLint)
- For performance profiling (use browser DevTools or dedicated profilers)
- As a replacement for code review

### Run full frontend quality suite (CI equivalent)

1. Run all frontend checks in sequence:
   ```bash
   make frontend-tests
   ```

2. This runs:
   - ESLint linting
   - Prettier formatting check
   - Unit tests with coverage
   - Optional: Type checking (if configured)

3. Address any failures before pushing

## Validation checklist

- [ ] All npm dependencies installed (`npm install` completes successfully)
- [ ] ESLint passes with no errors (`npm run lint` exits with 0)
- [ ] Prettier formatting is correct (`npm run format:check` passes)
- [ ] All unit tests pass (`npm run test` exits with 0)
- [ ] Coverage meets acceptable threshold (check `npm run test:coverage` output)
- [ ] No console.log or debug statements left in production code
- [ ] No unused imports or variables
- [ ] Type checking passes (if TypeScript is configured)
- [ ] Optional: fallow report reviewed if assessing code health

## Source of truth

- `package.json` — Node.js dependencies, scripts, and npm configuration
- `eslint.config.js` — ESLint rules and configuration
- `.prettierrc` or Prettier config in `package.json` — Code formatting rules
- `playwright.ui.config.mjs` — Playwright test configuration
- `.github/workflows/ci.yml` — `frontend-tests` job with exact validation steps
- `.github/workflows/nightly-autofix.yml` — Scheduled ESLint/Prettier autofix workflow
- `CONTRIBUTING.md` — Frontend coding standards and style guidelines

## Common failure modes and recovery actions

| Failure | Cause | Recovery |
|---------|-------|----------|
| `npm install` fails | Missing Node.js, npm version mismatch, or network issue | Verify Node.js 18+ installed; clear npm cache (`npm cache clean --force`); retry |
| ESLint errors | Code violates configured rules | Run `npm run lint:fix` for auto-fixable issues; manually fix remaining violations |
| Prettier formatting mismatch | Code doesn't match Prettier style | Run `npm run format` to auto-format; commit changes |
| Unit test failures | Code change breaks existing tests | Review test output, fix code logic, or update tests if expectations changed |
| `Cannot find module` error | Dependency not installed or import path wrong | Run `npm install`; verify import paths match exported names |
| Playwright test timeout | Browser automation taking too long | Increase timeout in `playwright.ui.config.mjs`; check for missing `await` in async code |
| `ENOENT: no such file or directory` in tests | Test files not found or path incorrect | Verify file paths in test configuration match actual files; check `playwright.ui.config.mjs` |

## Maintenance notes

- Review and refresh this skill **whenever frontend tooling changes** (ESLint version, Prettier config, Node.js LTS versions, fallow features)
- Update `last-reviewed` when changes are made to:
  - ESLint configuration (`eslint.config.js`)
  - Prettier configuration (`.prettierrc` or `package.json`)
  - Node.js version requirements
  - CI frontend-tests job (`.github/workflows/ci.yml`)
  - Nightly autofix workflow (`.github/workflows/nightly-autofix.yml`)
  - Fallow integration or health assessment standards

- Quarterly review should include:
  - Checking fallow reports for code health trends
  - Verifying ESLint and Prettier rules align with project standards
  - Assessing test coverage adequacy

## Writing standards

- Use imperative voice in workflow steps (e.g., "Run ESLint" not "Running...")
- Include exact npm script names and command-line examples
- Reference specific file paths (e.g., `pi_camera_in_docker/static/js/app.js` not "JavaScript files")
- Explain both successful paths and common failure recovery
- Keep validation checklist tied to concrete verification steps
- Document optional fallow usage with clear "when to use" guidelines
