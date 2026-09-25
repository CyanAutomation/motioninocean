---
name: feature-flag-management
description: Configure or change the mock-camera feature flag and keep its runtime integration documented. Use when testing without camera hardware or adding a supported flag.
owner: motion-in-ocean team
last-reviewed: 2026-09-25
category: Development
compatible-repo-areas:
  - pi_camera_in_docker/feature_flags.py
  - pi_camera_in_docker/feature_flag_usage_check.py
  - docs/guides/FEATURE_FLAGS.md
  - containers/
---

## Purpose

Configure the project’s active runtime flag correctly and prevent registry-only flags from being mistaken for implemented behavior.

## Scope and trigger conditions

- Use to enable mock camera mode or to add, change, or remove a runtime-integrated flag.
- The current registry has one active runtime flag: `MOCK_CAMERA`.
- Use [`pi-camera-troubleshooting`](../pi-camera-troubleshooting/SKILL.md) for camera-specific diagnosis.

## Required inputs

- The mode and environment where the flag will be set.
- Access to `pi_camera_in_docker/feature_flags.py`, the usage checker, and relevant tests.

## Step-by-step workflow

1. Read `docs/guides/FEATURE_FLAGS.md` and confirm the flag appears in `ACTIVE_RUNTIME_FLAGS` and has a concrete read in application code.
2. Set `MIO_MOCK_CAMERA=true` in the local process environment or the Docker Compose environment.
3. Restart the process or container after changing the environment.
4. Verify the effective configuration through `GET /api/feature-flags` or startup logs. Do not treat persisted settings or `PATCH /api/settings` as feature-flag controls.
5. For a new flag, add a runtime use, registry metadata, focused tests, documentation, and usage-check coverage in the same change.
6. Run `python -m pi_camera_in_docker.feature_flag_usage_check` and the relevant tests.

## Validation checklist

- [ ] Only flags with concrete runtime behavior are documented as active.
- [ ] The canonical `MIO_` environment variable is used in deployments.
- [ ] The flag’s default and invalid-value behavior match the documentation.
- [ ] `GET /api/feature-flags` reports the effective value.
- [ ] Tests cover enabled and disabled behavior.
- [ ] The feature-flag usage check passes.

## Source of truth

- `pi_camera_in_docker/feature_flags.py` — Active registry, environment prefix, defaults, and parsing.
- `pi_camera_in_docker/feature_flag_usage_check.py` — Static check for runtime flag usage.
- `docs/guides/FEATURE_FLAGS.md` — Supported flag and API contract.
- `containers/motion-in-ocean-webcam/docker-compose.yaml` — Compose environment mapping.
- `tests/unit/test_feature_flags.py` — Registry behavior tests.

## Common failure modes and recovery actions

- **Failure:** Mock mode is not enabled. **Recovery:** Check that `MIO_MOCK_CAMERA` is set in the container environment and recreate/restart the service.
- **Failure:** An older environment variable has no effect. **Recovery:** Use the canonical `MIO_MOCK_CAMERA` name; the legacy alias has been removed.
- **Failure:** A flag is listed but never changes runtime behavior. **Recovery:** Remove the unsupported entry or add and test the actual runtime integration before documenting it.
- **Failure:** A flag change is attempted through settings. **Recovery:** Configure the process environment and restart; feature flags are not editable application settings.

## Related Skills

- [`pi-camera-troubleshooting`](../pi-camera-troubleshooting/SKILL.md) — Diagnose real or mock camera startup.
- [`frontend-testing-linting`](../frontend-testing-linting/SKILL.md) — Validate frontend code that consumes flag data.
- [`ci-quality-gates`](../ci-quality-gates/SKILL.md) — Run the broader validation set.

## Maintenance notes

Review this skill when the registry, environment-variable parsing, API contract, or Compose configuration changes.
