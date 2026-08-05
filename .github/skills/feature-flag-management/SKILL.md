---
name: feature-flag-management
description: Enable, disable, and test motion-in-ocean feature flags; understand flag lifecycle and configure feature gate behavior for testing and production.
owner: motion-in-ocean team
last-reviewed: 2026-08-05
category: Development
compatible-repo-areas:
  - pi_camera_in_docker/feature_flags.py
  - pi_camera_in_docker/feature_flag_usage_check.py
  - docs/guides/FEATURE_FLAGS.md
  - Makefile
  - .env examples
  - tests/
---

## Purpose

Enable developers to understand, configure, test, and validate feature flags in motion-in-ocean. Feature flags control optional or experimental behaviors (e.g., mock camera mode, alternative adapters, debug features) without changing code. This skill covers enabling flags, testing flag-gated code paths, validating flag behavior, and understanding flag lifecycle from development through production.

## Scope and trigger conditions

Apply this skill when:

- Testing experimental features or beta functionality
- Enabling mock camera mode for development without hardware
- Testing feature gates and conditional code paths
- Debugging why a flag isn't taking effect
- Understanding available feature flags and their purposes
- Setting up feature flags for different environments (dev, staging, prod)
- Validating a feature flag implementation before merge

Do NOT use this skill for:

- Changing feature flag implementation code (that requires code review in PR)
- Deploying features without testing flag behavior
- Feature flag analytics or metrics (out of scope)
- Disabling critical safety features in production

## Required inputs

- Understanding of motion-in-ocean application modes (webcam, management)
- Access to environment variables or configuration files
- Ability to start/restart container or application
- Optional: `jq` or text editor for reviewing configuration

## Step-by-step workflow

### Understand available feature flags

1. **Review feature flag registry:**
   ```bash
   cat pi_camera_in_docker/feature_flags.py
   ```

2. **Look for the `get_feature_flags()` function** which defines all available flags

3. **Common feature flags:**
   - `mock_camera` — Use animated GIF instead of real camera hardware
   - `camera_adapter_<name>` — Alternative camera input adapters (experimental)
   - `debug_metrics` — Enable detailed debug metrics logging
   - `feature_name_here` — Other experimental features (see documentation for complete list)

4. **Review feature documentation:**
   ```bash
   cat docs/guides/FEATURE_FLAGS.md
   ```

5. **Document feature flags in environment:**
   - Each flag is controlled by environment variable (e.g., `MOCK_CAMERA`)
   - Look at examples in Makefile: `grep -A 5 "MOCK_CAMERA" Makefile`

### Enable a feature flag

1. **Option A: Environment variable (temporary, for local development)**
   ```bash
   export MOCK_CAMERA=true
   make run-mock
   # Or with Flask
   export MOCK_CAMERA=true
   python3 -m pi_camera_in_docker.main
   ```

2. **Option B: Docker/Docker Compose (persistent during container lifetime)**
   ```bash
   # In docker-compose.yml
   environment:
     MOCK_CAMERA: "true"
     APP_MODE: "webcam"
   ```

3. **Option C: .env file (for docker-compose)**
   ```bash
   # Create or edit .env
   echo "MOCK_CAMERA=true" >> .env
   docker compose up
   ```

4. **Option D: Via config/settings (if implemented)**
   - Some flags may be settable via `/api/settings` POST endpoint
   - Requires authentication token
   - Persists in application settings file

### Verify feature flag is enabled

1. **Check if flag is actually enabled:**
   ```bash
   # Method 1: Check environment variable
   echo $MOCK_CAMERA
   # Expected output: true
   
   # Method 2: Check running container
   docker exec <container-id> env | grep MOCK_CAMERA
   ```

2. **Check via application introspection:**
   ```bash
   # If available, check feature flag status via API
   curl -H "Authorization: Bearer <token>" http://localhost:8000/api/status | jq '.features'
   ```

3. **Observe flag effects in logs:**
   ```bash
   docker compose logs motion-in-ocean | grep -i "mock\|camera\|feature"
   ```

### Test mock camera mode

1. **Enable mock camera:**
   ```bash
   export MOCK_CAMERA=true
   make run-mock
   ```

2. **Expected behavior:**
   - Application starts without requiring camera hardware
   - Logs show "Mock camera mode enabled"
   - `/stream` endpoint returns animated cat GIF frames
   - `/api/status` shows camera as operational despite no hardware

3. **Test streaming:**
   ```bash
   curl http://localhost:8000/stream -v 2>&1 | head -50
   ```

4. **Expected output:**
   - HTTP 200 response
   - MJPEG stream with GIF frames
   - Should see JPEG data in response body

### Test feature flag code paths

1. **Identify what code is gated by the flag:**
   - Search codebase for flag name: `grep -r "mock_camera\|MOCK_CAMERA" pi_camera_in_docker/ --include="*.py"`
   - Review the conditional logic to understand what changes

2. **Create tests for both enabled/disabled states:**
   ```bash
   # Run tests with mock disabled
   MOCK_CAMERA=false make test
   
   # Run tests with mock enabled
   MOCK_CAMERA=true make test
   ```

3. **Verify expected behavior:**
   - Mock enabled: Should use fallback GIF instead of camera
   - Mock disabled: Should attempt real camera initialization

4. **Test in isolation (if possible):**
   ```bash
   # Run a specific test with flag enabled
   MOCK_CAMERA=true python -m pytest tests/test_mock_stream_renderer.py -v
   ```

### Validate feature flag configuration

1. **Check feature flag usage across codebase:**
   ```bash
   python3 pi_camera_in_docker/feature_flag_usage_check.py
   ```

2. **Expected output:** No errors; flags are used consistently

3. **If errors found:**
   - Fix imports or usage patterns
   - Ensure flag names match registry
   - Run check again to verify

### Document feature flag for production use

1. **Before deploying, document:**
   - What the flag controls
   - How to enable/disable
   - Default behavior (enabled or disabled)
   - Any side effects or incompatibilities
   - Required for production or experimental only

2. **Update deployment documentation:**
   - Add to `docs/guides/DEPLOYMENT.md` if it affects deployments
   - Document environment variable in `docs/ENVIRONMENT_VARIABLES_DOCUMENTATION_COMPLETE.md`

3. **Example documentation:**
   ```markdown
   ### MOCK_CAMERA
   
   **Purpose:** Use animated test GIF instead of real camera hardware  
   **Default:** false  
   **Type:** boolean  
   **Example:** `MOCK_CAMERA=true`  
   **Compatibility:** All modes (webcam, management)  
   **Production Use:** Development and testing only; do NOT use in production
   ```

### Disable a feature flag

1. **Remove environment variable:**
   ```bash
   unset MOCK_CAMERA
   ```

2. **Or set to false:**
   ```bash
   export MOCK_CAMERA=false
   ```

3. **Restart application/container:**
   ```bash
   # For development
   Ctrl+C  # stop current process
   make run  # restart
   
   # For Docker
   docker compose down
   docker compose up
   ```

### Handle flag conflicts or unexpected behavior

1. **Identify if flag is causing issue:**
   - Disable all experimental flags
   - Restart application
   - Test core functionality
   - If works, flag was the issue

2. **Debug flag state:**
   ```bash
   # Check all environment variables
   env | grep -i flag
   env | grep -i mock
   
   # Check container environment
   docker exec <container-id> env | sort
   ```

3. **Check feature flag implementation:**
   ```bash
   # Review how flag is evaluated
   grep -A 10 "def is_enabled" pi_camera_in_docker/feature_flags.py
   ```

4. **Review recent changes:**
   - Check if flag was recently added/modified
   - Review git history: `git log -p pi_camera_in_docker/feature_flags.py | head -100`

## Related Skills

- **UI feature gating:** Use [`ui-playwright`](../ui-playwright/SKILL.md) to test UI with flag enabled/disabled
- **Frontend implementation:** Use [`frontend-testing-linting`](../frontend-testing-linting/SKILL.md) for JS/TS code with feature gates
- **Development workflow:** Use [`contributor-workflow`](../contributor-workflow/SKILL.md) which references this skill
- **Mock camera development:** Use this skill to enable `MOCK_CAMERA` flag for non-Pi testing

## Validation checklist

- [ ] Feature flag is defined in `pi_camera_in_docker/feature_flags.py`
- [ ] Feature flag environment variable is set correctly (`export FLAG_NAME=true`)
- [ ] Application respects the flag setting (observable in logs or behavior)
- [ ] Both enabled and disabled states tested
- [ ] Code paths gated by flag execute correctly
- [ ] No conflicts with other flags
- [ ] Documentation updated if flag is user-facing
- [ ] Tests pass for both flag states (if applicable)

## Source of truth

- `pi_camera_in_docker/feature_flags.py` — Registry of all available feature flags
- `pi_camera_in_docker/feature_flag_usage_check.py` — Validation script for flag usage consistency
- `docs/guides/FEATURE_FLAGS.md` — Feature flag documentation and user guidance
- `pi_camera_in_docker/main.py` — Feature flag initialization and loading
- `CONTRIBUTING.md` — Development guidelines for adding new flags
- `.env.example` or docker-compose examples — Configuration examples with flags

## Common failure modes and recovery actions

| Failure | Cause | Recovery |
|---------|-------|----------|
| Flag doesn't take effect | Environment variable not set, or app not restarted | Verify `echo $FLAG_NAME` shows correct value; restart application; check app actually reads the flag |
| Mock camera returns real stream | `MOCK_CAMERA` set to false or not set | Set `MOCK_CAMERA=true`; restart container; verify logs show "Mock camera mode" |
| Flag set in one place but not another | Inconsistent configuration across environments | Use `.env` file for docker-compose; or set in shell before running; check all places flag could be set |
| Feature flag usage check fails | Inconsistent flag usage in code | Run `python3 pi_camera_in_docker/feature_flag_usage_check.py`; fix reported issues; rerun check |
| Tests fail with flag enabled that pass without | Flag behavior conflicts with test expectations | Update tests to handle both flag states; or fix flag implementation |
| Unexpected behavior with multiple flags | Flag combinations create conflicts | Test flags individually first; then test combinations; document any incompatible pairs |
| Docker container doesn't pick up flag | Environment variable not passed to container | Use docker-compose environment section; or docker `--env` flag; or .env file for compose |

## Maintenance notes

- Review and refresh this skill **when feature flags are added, removed, or behavior changes**
- Update `last-reviewed` when changes are made to:
  - Feature flag registry (`pi_camera_in_docker/feature_flags.py`)
  - Feature flag usage check (`pi_camera_in_docker/feature_flag_usage_check.py`)
  - Feature flag documentation (`docs/guides/FEATURE_FLAGS.md`)
  - Major flag behavior changes or new flags added

- Regular maintenance tasks:
  - Quarterly: Review active flags and deprecate obsolete ones
  - Before each release: Document which flags are stable vs. experimental
  - When merging feature branches: Validate new flags are registered and documented

## Writing standards

- Use imperative voice in workflow steps (e.g., "Enable a feature flag" not "Enabling...")
- Include exact environment variable names and values
- Explain both success and failure scenarios
- Keep validation checklist tied to observable flag behavior
- Document feature flags clearly in production use sections
- Include examples of flag combinations and potential conflicts
