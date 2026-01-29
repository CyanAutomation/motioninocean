# Branch Protection Recommendations

This document provides recommended branch protection rules for the motion-in-ocean repository.

## Repository Settings

### Branch Protection Rules for `main`

Navigate to: **Settings → Branches → Add branch protection rule**

#### Protection Rule Configuration

**Branch name pattern:** `main`

#### Recommended Settings

✅ **Require a pull request before merging**
- Require approvals: 1
- Dismiss stale pull request approvals when new commits are pushed
- Require review from Code Owners

✅ **Require status checks to pass before merging**
- Require branches to be up to date before merging
- Status checks that are required:
  - `test (3.9)` - Python 3.9 tests
  - `test (3.11)` - Python 3.11 tests
  - `test (3.12)` - Python 3.12 tests
  - `lint` - Ruff linting
  - `type-check` - Mypy type checking
  - `security` - Bandit security scan

✅ **Require conversation resolution before merging**

✅ **Require linear history**

✅ **Include administrators** (recommended for consistency)

#### Optional Settings

⚪ **Require signed commits** - Enable if you want commit signing enforcement

⚪ **Require deployments to succeed before merging** - If you add deployment workflows

#### Not Recommended

❌ **Allow force pushes** - Keep disabled to maintain history integrity

❌ **Allow deletions** - Keep disabled to protect main branch

---

## Additional Repository Settings

### General Settings

Navigate to: **Settings → General**

#### Pull Requests

✅ **Allow squash merging** - Keeps history clean
- Default to pull request title

✅ **Allow merge commits** - Useful for feature branches
- Default to pull request title

❌ **Allow rebase merging** - Disable to avoid confusion

✅ **Automatically delete head branches** - Keeps repo clean

#### Features

✅ **Issues** - Enable for bug tracking
✅ **Discussions** - Enable for community questions
✅ **Sponsorships** - Optional

---

## Security Settings

Navigate to: **Settings → Security**

### Code Security and Analysis

✅ **Dependency graph** - Enable (should be enabled by default)

✅ **Dependabot alerts** - Enable for vulnerability notifications

✅ **Dependabot security updates** - Enable for automatic security patches

✅ **Dependabot version updates** - Already configured via `.github/dependabot.yaml`

✅ **Code scanning** - Enable GitHub Advanced Security if available
- Trivy scanning is already configured via workflow

✅ **Secret scanning** - Enable for credential leak detection

---

## Workflow Permissions

Navigate to: **Settings → Actions → General → Workflow permissions**

Recommended: **Read and write permissions**
- Allow GitHub Actions to create pull requests: ✅

This allows Dependabot and other automations to work properly.

---

## Ruleset Example (Modern Alternative)

GitHub now offers Rulesets as an alternative to branch protection rules. Here's a recommended configuration:

Navigate to: **Settings → Rules → Rulesets → New ruleset**

**Ruleset name:** `main-branch-protection`

**Target:** Default branch

### Rules

1. **Require pull request**
   - Required approvals: 1
   - Dismiss stale reviews: Yes
   - Require code owner review: Yes

2. **Require status checks**
   - Require all checks to pass
   - Status checks:
     - `test (3.9)`
     - `test (3.11)`
     - `test (3.12)`
     - `lint`
     - `type-check`
     - `security`

3. **Block force pushes**

4. **Require linear history**

---

## Enforcement Timeline

### Immediate (Day 1)
1. Enable Dependabot alerts
2. Enable secret scanning
3. Set up basic branch protection on `main`

### Week 1
1. Configure full branch protection rules
2. Enable Dependabot security updates
3. Train team on PR workflow

### Week 2
1. Review and refine status check requirements
2. Enable conversation resolution requirement
3. Document exceptions process

---

## Exceptions Process

For urgent hotfixes or exceptional circumstances:

1. Create a bypass request in an issue
2. Document the reason and approval
3. Create the hotfix with elevated permissions
4. Follow up with a post-mortem if applicable

---

## Monitoring and Review

### Quarterly Review
- Check if status checks are passing reliably
- Review bypass exceptions (if any)
- Update required checks based on workflow changes

### After Major Changes
- Verify new CI jobs are added to required checks
- Test branch protection with a test PR
- Update this document with any changes

---

## References

- [GitHub Branch Protection Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub Rulesets Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [Dependabot Configuration](https://docs.github.com/en/code-security/dependabot)
