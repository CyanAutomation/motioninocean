---
name: dependabot-dependency-management
description: Review, test, and merge Dependabot pull requests for Python and JavaScript/TypeScript dependencies; handle version updates, security patches, and dependency conflicts.
owner: motion-in-ocean team
last-reviewed: 2026-08-05
category: CI/CD
compatible-repo-areas:
  - .github/dependabot.yml
  - requirements.txt
  - requirements-dev.txt
  - package.json
  - package-lock.json
  - Dockerfile
  - Makefile
  - .github/workflows/ci.yml
---

## Purpose

Enable developers and maintainers to safely review, test, and merge automated dependency updates from Dependabot. Motion-in-ocean uses Dependabot to monitor Python (pip), JavaScript/TypeScript (npm), Docker images, and GitHub Actions for updates and security vulnerabilities. This skill covers understanding Dependabot configuration, reviewing PRs, running tests, resolving conflicts, and deciding when to merge or defer updates.

## Scope and trigger conditions

Apply this skill when:

- A Dependabot pull request is created for dependency updates
- Security advisories are published for motion-in-ocean dependencies
- Dependency version conflicts need resolution
- Testing needs to verify updates don't break functionality
- Deciding which Dependabot PRs to merge and which to defer
- Configuring Dependabot behavior or update schedules
- Troubleshooting failed dependency update PR

Do NOT use this skill for:

- Adding new dependencies (use pip install or npm install + commit to files)
- Manual version pinning or major version downgrades (requires discussion/review)
- Non-Dependabot dependency updates
- Comprehensive dependency audit or security scanning (separate workflow)

## Required inputs

- GitHub repository access with permission to view/merge PRs
- Python 3.9+ and Node.js 18+ for local testing
- `pip` and `npm` CLI tools
- Basic understanding of semantic versioning (MAJOR.MINOR.PATCH)
- CI workflow visibility to check test status

## Step-by-step workflow

### Understand Dependabot configuration

1. **Review Dependabot settings:**
   ```bash
   cat .github/dependabot.yml
   ```

2. **Key configuration sections:**
   - `version: 2` — Dependabot v2 API
   - `updates:` — List of package managers to monitor
   - Common managers: `pip`, `npm`, `docker`, `github-actions`

3. **Understand update schedule:**
   - `schedule.interval` — How often Dependabot checks for updates (daily, weekly, monthly)
   - `schedule.day` — Preferred day of week for updates
   - `schedule.time` — Preferred time for update PRs

4. **Review Dependabot version grouping:**
   - `groups` — Group related updates into single PR (if configured)
   - Without grouping: One PR per dependency update
   - With grouping: Multiple updates combined into one PR

### Monitor Dependabot PRs

1. **Find Dependabot pull requests:**
   - Go to repository's Pull Requests tab
   - Filter by `author:dependabot-preview` or `author:dependabot`
   - Or search for "Dependabot" in PR title

2. **Understand PR structure:**
   - Title: `[Package Manager] Bump <package> from X.Y.Z to A.B.C`
   - Description: Lists all changed packages and versions
   - CI status shown: Test results, coverage changes, any CI failures

3. **Check PR status signals:**
   - ✅ All checks passed — Safe to merge
   - ❌ Some checks failed — May need investigation or version compatibility fixes
   - ⏳ Checks in progress — Wait for all checks to complete

### Review a Dependabot PR

1. **Read the PR description:**
   - Identifies package name and old/new versions
   - May include release notes link
   - Shows if it's a major/minor/patch version update

2. **Check the "Files changed" tab:**
   - Review which dependency files changed
   - Look for any unexpected changes (Dependabot should only change version numbers)
   - Verify lock files are updated (package-lock.json, etc.)

3. **Assess the update type:**
   - **Patch (x.y.Z)** — Usually safe, bug fixes and minor improvements
   - **Minor (x.Y.z)** — Generally safe, new features but backward compatible
   - **Major (X.y.z)** — Requires more scrutiny, may have breaking changes

4. **Check for security advisories:**
   - PR title or description mentions "security" or has a red banner
   - Security updates should typically be prioritized for merge

5. **Review dependency compatibility:**
   - For Python: Check if package has minimum version requirements that conflict
   - For Node.js: Check if package versions are compatible with existing peer dependencies

### Test a Dependabot PR locally

1. **Check out the PR branch:**
   ```bash
   # GitHub CLI (if configured)
   gh pr checkout <PR-number>
   # OR manually
   git fetch origin pull/<PR-number>/head:dependabot-update
   git checkout dependabot-update
   ```

2. **Install updated dependencies:**
   ```bash
   # For Python
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   
   # For Node.js
   npm install
   ```

3. **Run test suite:**
   ```bash
   # Python tests
   make test
   # Or specific test group
   make test-unit
   make test-integration
   
   # Frontend tests (if dependencies changed)
   npm run test
   ```

4. **Run linting and type checks:**
   ```bash
   make lint
   make type-check
   npm run lint
   ```

5. **Test application behavior (if relevant):**
   ```bash
   # Start application with updated deps
   export MOCK_CAMERA=true
   make run-mock
   
   # In another terminal, test endpoints
   curl http://localhost:8000/health
   curl http://localhost:8000/stream
   ```

6. **Check for deprecation warnings:**
   - Run tests and app startup
   - Watch for `DeprecationWarning` messages
   - If found, may need to update code to use new API before updating dependency

### Resolve dependency conflicts

1. **Identify the conflict:**
   - Test fails with version incompatibility error
   - E.g., "Package A requires B >= 1.0, but updated to B 2.0 which is incompatible"

2. **Investigate root cause:**
   ```bash
   # For Python
   pip show <package-name>  # Check installed version
   pip index versions <package-name>  # Check available versions
   
   # For Node.js
   npm view <package-name> versions  # List all versions
   npm ls <package-name>  # Show dependency tree
   ```

3. **Resolution options:**
   - **Update both packages together** — If both have compatible newer versions
   - **Pin conflicting dependency** — Lock to specific version in requirements.txt or package.json
   - **Defer update** — Leave comment on PR and skip this update cycle
   - **Report to maintainers** — If incompatibility is in upstream packages (rare)

4. **If conflict can't be resolved:**
   - Comment on PR with findings
   - Apply label `dependencies/blocked` or similar
   - Defer to next release cycle

### Decide whether to merge

1. **Merge immediately if:**
   - All tests pass ✅
   - It's a patch or minor version update
   - No deprecation warnings
   - It's a security update

2. **Merge with caution if:**
   - Major version update (requires code review)
   - Breaking changes documented in release notes
   - Only test failures are related to new package version (not existing bugs)

3. **Defer merge if:**
   - Critical tests fail
   - Dependency conflicts with essential packages
   - Major version with significant API changes needing code updates
   - Security update is for non-critical package (can batch with other updates)

4. **Comment on PR if deferring:**
   ```markdown
   Deferring this update to [version/timeframe] because:
   - [specific reason]
   - [what needs to be fixed before merge]
   ```

5. **Apply labels:**
   - `dependencies` — General dependency update
   - `dependencies/security` — Security patch
   - `dependencies/review` — Needs manual review
   - `dependencies/blocked` — Conflict, can't merge now

### Merge the PR

1. **Ensure all checks passed:**
   - GitHub shows ✅ all checks completed
   - Manually verify if needed: click "Show all checks"

2. **Choose merge method:**
   - **Squash and merge** (recommended) — Cleans up commit history
   - **Create a merge commit** — Preserves Dependabot commit message
   - **Rebase and merge** — Not recommended (can cause issues with auto-updates)

3. **Merge:**
   - Click "Merge pull request"
   - Confirm merge
   - Optionally delete the PR branch

4. **Monitor for issues:**
   - After merge, watch for any new CI failures in main branch
   - If issues appear, may need to revert and investigate

### Handle Dependabot configuration changes

1. **To change update schedule:**
   - Edit `.github/dependabot.yml`
   - Change `schedule.interval` (daily, weekly, monthly)
   - Commit and push
   - Dependabot will adjust next scheduled run

2. **To add a new package manager:**
   - Add new `updates:` section in `.github/dependabot.yml`
   - Specify package manager and directory
   - Example for Docker:
     ```yaml
     - package-ecosystem: docker
       directory: "/"
       schedule:
         interval: weekly
     ```

3. **To disable Dependabot:**
   - Delete `.github/dependabot.yml` OR comment out all updates
   - OR use the GitHub Settings UI to disable

### Handle Dependabot holidays/batching

1. **Dependabot batching:**
   - If multiple updates available, Dependabot may batch minor/patch updates together
   - Major version updates usually get separate PRs

2. **Holiday periods:**
   - Dependabot respects GitHub holiday schedules
   - PRs may not be created during major holidays

3. **Manual trigger (if needed):**
   - GitHub Actions allows manual Dependabot workflow trigger
   - Or close/reopen Dependabot PR to reset its state

## Validation checklist

- [ ] Dependabot PR clearly shows old and new versions
- [ ] All CI checks have completed (test, lint, security)
- [ ] No deprecation warnings in test output
- [ ] Compatibility verified with existing code (no conflicts)
- [ ] Security updates prioritized and merged quickly
- [ ] Major version updates reviewed for breaking changes
- [ ] Updated dependencies installed successfully locally
- [ ] Application tested with updated dependencies
- [ ] PR labeled appropriately (security, review, etc.)
- [ ] Merge decision documented if deferring

## Source of truth

- `.github/dependabot.yml` — Dependabot configuration, update schedule, and package managers
- `requirements.txt` — Python production dependencies
- `requirements-dev.txt` — Python development dependencies
- `package.json` — JavaScript/TypeScript dependencies and version pinning
- `package-lock.json` — Locked JavaScript dependency versions (auto-updated by npm)
- `Dockerfile` — Base image versions and OS dependencies
- `.github/workflows/ci.yml` — Test requirements for dependency updates
- `CHANGELOG.md` — Release notes to understand what changed in updates

## Common failure modes and recovery actions

| Failure | Cause | Recovery |
|---------|-------|----------|
| Dependency update breaks tests | Package has breaking changes or API differs | Review package release notes; check if code needs updates; defer if significant changes needed |
| Import error after update | Module moved or renamed in new version | Check package migration guide; update imports in code; test locally |
| Version conflict (A requires B@1.0, got B@2.0) | Transitive dependency conflict | Check if another dependency pins B to different version; may need to update both together |
| Dependabot PR has merge conflicts | Main branch changed since PR created | GitHub usually auto-resolves; if not, close and re-open PR for Dependabot to update |
| Tests pass but application crashes | Issue only appears at runtime, not in tests | Manually test the application; may need to add test coverage for the crash scenario |
| Security update fails tests | Breaking change in security patch | Rare, but report to package maintainers; apply temporary pin until fixed upstream |
| Too many Dependabot PRs | High update frequency due to large dependency tree | Consider batching: update `.github/dependabot.yml` to group updates or increase interval |

## Maintenance notes

- Review and refresh this skill **quarterly** and **when Dependabot configuration changes**
- Update `last-reviewed` when changes are made to:
  - Dependabot configuration (`.github/dependabot.yml`)
  - CI/test requirements that affect Dependabot updates
  - Major dependency version strategy
  - Security advisory handling process

- Regular monitoring tasks:
  - Weekly: Review open Dependabot PRs and merge ready ones
  - Monthly: Review update trends and dependency health
  - Quarterly: Assess if Dependabot schedule (daily/weekly/monthly) is appropriate

## Writing standards

- Use imperative voice in workflow steps (e.g., "Merge the PR" not "Merging...")
- Include exact commands and file paths
- Explain semantic versioning context (major/minor/patch)
- Keep validation checklist tied to observable CI and test results
- Document both automated and manual decision points clearly
- Explain when to prioritize security updates vs. routine updates
