---
name: nightly-autofix-workflow
description: Understand, monitor, and troubleshoot the scheduled nightly code quality automation (ESLint, Ruff, Prettier) that creates automated pull requests.
owner: motion-in-ocean team
last-reviewed: 2026-08-05
category: CI/CD
compatible-repo-areas:
  - .github/workflows/nightly-autofix.yml
  - eslint.config.js
  - pyproject.toml
  - package.json
  - Makefile
---

## Purpose

Enable developers to understand and troubleshoot the automated nightly code quality workflow that runs on a schedule and creates pull requests with code fixes. The nightly autofix workflow runs ESLint, Ruff, and Prettier on a schedule to maintain consistent code style and fix common quality issues automatically. This skill covers understanding the workflow, monitoring scheduled runs, handling failed autofix PRs, and resolving merge conflicts.

## Scope and trigger conditions

Apply this skill when:

- Understanding how the nightly autofix workflow works
- Debugging failed nightly autofix workflow runs
- Handling merge conflicts in automatically generated autofix PRs
- Reviewing or merging nightly autofix pull requests
- Temporarily disabling the autofix workflow
- Investigating why autofix didn't fix an issue
- Understanding the cron schedule and what time the workflow runs

Do NOT use this skill for:

- Running autofix manually on demand (use individual `make format`, `make lint-fix` commands instead)
- Fixing code quality issues unrelated to ESLint/Ruff/Prettier
- Troubleshooting other GitHub Actions workflows
- Changing the autofix workflow behavior (that requires editing `.github/workflows/nightly-autofix.yml`)

## Required inputs

- GitHub Actions workflow visibility (access to `.github/workflows/` in the repository)
- GitHub Actions run history accessible via repository Actions tab
- Git knowledge to handle merge conflicts
- Access to merge/commit permissions if approving autofix PRs

## Step-by-step workflow

### Understanding the nightly autofix workflow

1. Review the workflow file:
   ```bash
   cat .github/workflows/nightly-autofix.yml
   ```

2. Key workflow information:
   - **Schedule:** Runs on a cron schedule (typically 2 AM UTC daily)
   - **What it does:** Runs ESLint auto-fix, Ruff auto-fix, and Prettier formatting on the entire codebase
   - **Commit behavior:** Creates a commit with changes if any fixes are needed
   - **PR creation:** If commits were made, opens/updates a pull request
   - **Branch:** Commits to a dedicated branch (e.g., `nightly-autofix` or `chore/nightly-quality-fixes`)

3. Understand the execution order:
   - Step 1: Checkout main branch
   - Step 2: Setup Node.js and Python environments
   - Step 3: Install dependencies (`npm install`, `pip install -r requirements-dev.txt`)
   - Step 4: Run ESLint auto-fix (`npm run lint:fix`)
   - Step 5: Run Ruff auto-fix (`make lint-fix`)
   - Step 6: Run Prettier formatting (`npm run format`)
   - Step 7: Commit changes (if any)
   - Step 8: Push commits and create/update PR

### Monitor scheduled workflow runs

1. Navigate to the repository's Actions tab on GitHub

2. Look for the "Nightly Autofix" or similar workflow name

3. View recent runs:
   - Click on the workflow name
   - Scroll through the run history
   - Check status: ✅ Success, ❌ Failed, ⏭️ Skipped

4. Understand run status meanings:
   - **Success:** Autofix ran, checked code, and created/updated PR if fixes were needed
   - **Failed:** An error occurred during the workflow (linting tool failure, git push failure, PR creation failure)
   - **Skipped:** Workflow didn't run (may be disabled or schedule condition not met)

5. View workflow run details:
   - Click on a run to see step-by-step execution logs
   - Review which step failed (if status is Failed)
   - Check the logs for error messages

### Handle failed nightly autofix runs

1. **Identify the failure:**
   - Click the failed workflow run
   - Review the logs for the step that failed
   - Common failure points: checkout, install dependencies, lint/format execution, git push, PR creation

2. **Failure: Dependency installation failed**
   - Cause: `npm install` or `pip install` failed due to network or version conflict
   - Recovery:
     - Manual fix: Run `npm install` and `pip install -r requirements-dev.txt` locally; push fixes to main
     - Or wait for next scheduled run (24 hours later)
     - Or manually trigger the workflow from Actions tab (if available)

3. **Failure: Linting/formatting step failed**
   - Cause: ESLint or Ruff encountered a syntax error in code or configuration
   - Recovery:
     - Run locally to reproduce: `npm run lint:fix && make lint-fix && npm run format`
     - Fix any reported errors in the codebase
     - Push fixes to main
     - Workflow will pick up fixes on next run

4. **Failure: Git push or PR creation failed**
   - Cause: Permissions issue, branch protection rule, or secrets not configured
   - Recovery:
     - Verify the workflow has `GITHUB_TOKEN` configured (typically automatic in GitHub Actions)
     - Check repository branch protection rules don't block the autofix branch
     - Contact repository maintainer if secrets are misconfigured

### Review and merge nightly autofix PRs

1. **Monitor autofix PR:**
   - GitHub will create a PR titled "Nightly Autofix" or similar
   - PR branches from `nightly-autofix` branch or similar dedicated branch
   - Subsequent runs may update the same PR by adding commits

2. **Review PR changes:**
   - Review files changed tab to see what was fixed
   - Check if changes are expected (formatting, linting fixes)
   - If changes look incorrect, comment and ask for manual review

3. **Handle merge conflicts:**
   - If autofix branch conflicts with main, the PR will show a conflict marker
   - Cause: Manual commits to main since autofix branch was created
   - Recovery:
     - Option A (manual rebase):
       ```bash
       git checkout nightly-autofix
       git rebase main
       git push --force-with-lease origin nightly-autofix
       ```
     - Option B (wait for next autofix run to automatically update)
     - Option C (close PR and let next scheduled run create a fresh one)

4. **Merge the PR:**
   - Once approved and tests pass, merge normally
   - Use "Squash and merge" or "Create a merge commit" (not "Rebase and merge" to preserve commit history)
   - After merge, the autofix branch may be automatically deleted

5. **After merge:**
   - Next scheduled autofix run will rebase on the new main
   - If no changes are needed, no new PR will be created

### Temporarily disable the nightly autofix workflow

1. **Disable via GitHub UI:**
   - Go to Actions tab
   - Find "Nightly Autofix" workflow
   - Click the "..." menu (top-right of workflow card)
   - Select "Disable workflow"

2. **Re-enable via GitHub UI:**
   - Follow same steps as above
   - Click "..." menu
   - Select "Enable workflow"

3. **Disable via code (permanent):**
   - Edit `.github/workflows/nightly-autofix.yml`
   - Change the `on:` schedule trigger to commented-out or removed
   - Commit and push
   - Note: This requires a PR and review

### Manually trigger the autofix workflow (if needed)

1. **Go to Actions tab**

2. **Select "Nightly Autofix" workflow**

3. **Click "Run workflow" button** (if available)

4. **Select branch:** Usually defaults to `main`

5. **Click "Run workflow" to execute immediately**

6. **Monitor the run** in the workflow history

## Validation checklist

- [ ] Workflow file `.github/workflows/nightly-autofix.yml` exists and is valid YAML
- [ ] Workflow runs are visible in the repository's Actions tab
- [ ] Autofix PR was created (if there were code quality fixes needed)
- [ ] ESLint, Ruff, and Prettier outputs are as expected
- [ ] Merge conflicts (if any) are resolved or understood
- [ ] Autofix PR is reviewed and either merged or explicitly closed with notes

## Source of truth

- `.github/workflows/nightly-autofix.yml` — Exact workflow definition, schedule, and job steps
- `eslint.config.js` — ESLint auto-fix rules and configuration
- `pyproject.toml` and Makefile — Ruff auto-fix configuration
- `package.json` — Prettier configuration and npm scripts
- Repository branch protection settings — May affect autofix push/PR creation
- GitHub Actions documentation — For workflow triggers and environment variables

## Common failure modes and recovery actions

| Failure | Cause | Recovery |
|---------|-------|----------|
| Workflow fails to run at scheduled time | Workflow disabled, schedule syntax error, or GitHub Actions service issue | Verify workflow is enabled; check cron syntax in YAML; wait for next schedule or manually trigger |
| Autofix PR shows merge conflicts | Main branch advanced since autofix branch created | Rebase autofix branch (`git rebase main`); or wait for next scheduled run; or close and recreate |
| Autofix made unwanted changes | Configuration in ESLint/Ruff/Prettier is too aggressive | Review rule configuration; update if needed; or manually revert changes in PR before merge |
| ESLint/Ruff step fails with "No such file" | Dependencies not installed or path incorrect | Manually run `npm install` and `pip install -r requirements-dev.txt`; verify files exist |
| Autofix PR not created even though fixes were made | Git push failed, or PR creation blocked by branch protection | Check workflow logs for error; verify branch protection settings; ensure GITHUB_TOKEN has push permissions |
| Multiple autofix PRs exist | Previous PR not merged/closed before next run | Close old PR; merge new one; next run will update accordingly |
| Changes to code get reverted by autofix on next run | Auto-fix rules are too strict or conflicting with manual changes | Review auto-fix configuration; discuss as team whether to loosen rules or exclude certain files |

## Maintenance notes

- Review and refresh this skill **quarterly** and **whenever nightly-autofix workflow changes**
- Update `last-reviewed` when changes are made to:
  - Workflow file (`.github/workflows/nightly-autofix.yml`)
  - ESLint configuration (`eslint.config.js`)
  - Ruff configuration (`pyproject.toml`, Makefile)
  - Prettier configuration (`package.json`)
  - Branch protection or GitHub Actions permissions settings

- Monitoring tasks:
  - Weekly: Check autofix PR status and merge if approved
  - Quarterly: Review workflow run history for patterns (failures, merge conflicts)
  - As-needed: Adjust workflow schedule if 2 AM UTC doesn't align with team timezone

## Writing standards

- Use imperative voice in workflow steps (e.g., "Review PR changes" not "Reviewing...")
- Include exact file paths and workflow names
- Explain both successful workflow execution and common failure scenarios
- Keep validation checklist tied to observable workflow outputs
- Document troubleshooting with specific log patterns and recovery steps
