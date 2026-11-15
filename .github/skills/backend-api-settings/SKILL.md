---
name: backend-api-settings
description: Add or change Motion In Ocean API routes, request/response contracts, or editable settings. Use when backend changes affect authentication, OpenAPI, validation, defaults, or persisted settings.
owner: motion-in-ocean team
last-reviewed: 2026-11-15
category: Development
compatible-repo-areas:
  - pi_camera_in_docker/settings_api.py
  - pi_camera_in_docker/settings_schema.py
  - pi_camera_in_docker/management_api.py
  - docs/openapi.json
  - tests/test_management_api.py
  - tests/test_openapi.py
---

## Purpose

Keep backend behavior, versioned API contracts, settings validation, persistence, generated API documentation, and tests consistent.

## Scope and trigger conditions

- Use when adding or changing a Flask API endpoint or management operation.
- Use when changing a setting, its schema, environment default, validation, persistence, or reset behavior.
- Use [`api-security-review`](../api-security-review/SKILL.md) when a change affects authentication, untrusted URLs, credentials, or network trust boundaries.
- Use [`ci-quality-gates`](../ci-quality-gates/SKILL.md) for the full local validation suite.

## Required inputs

- The requested API or settings behavior and the application mode(s) it affects.
- Existing route implementation, schema/configuration source, OpenAPI contract, and related tests.
- The intended authentication boundary and backward-compatibility expectations.

## Step-by-step workflow

1. Trace the route registration and current versioned path. New API clients should use `/api/v1/...`; preserve documented legacy redirects unless explicitly deprecating them.
2. Identify whether the route is public, protected by webcam authentication, or protected by management authentication. Keep authorization checks at the established boundary.
3. For a settings change, update `SettingsSchema`, config validation, environment defaults, and atomic persistence behavior as applicable. Preserve the documented precedence: environment values, persisted overrides, then schema defaults.
4. Write or update a focused test first for the expected response, validation failure, authorization result, or persistence behavior; confirm the test fails for the intended reason before implementing the change.
5. Update `docs/openapi.json` and related API or deployment documentation when the public contract changes. Keep error codes, status codes, and examples aligned with the implementation.
6. Run the focused tests, then the relevant broader checks:

   ```bash
   .venv/bin/python -m pytest tests/test_management_api.py tests/test_openapi.py -q
   ```

7. Review the final diff for accidental secret exposure, stale legacy paths, and mismatch among route behavior, schema, tests, and documentation.

## Validation checklist

- [ ] Versioned route, methods, status codes, and error response match the intended contract.
- [ ] Authentication behavior is tested for permitted and rejected requests.
- [ ] Settings defaults, constraints, environment overrides, persistence, and reset behavior agree.
- [ ] Invalid payloads fail without partially persisting changes.
- [ ] OpenAPI and user-facing documentation match the API behavior.
- [ ] Relevant tests pass and include the new or changed behavior.

## Source of truth

- `pi_camera_in_docker/management_api.py` — Management routes, node operations, and route protection.
- `pi_camera_in_docker/settings_api.py` — Settings endpoints and request handling.
- `pi_camera_in_docker/settings_schema.py` and `pi_camera_in_docker/config_validator.py` — Editable setting definitions and validation.
- `pi_camera_in_docker/application_settings.py` and `pi_camera_in_docker/runtime_config.py` — Persistence and effective configuration precedence.
- `docs/openapi.json` — Checked-in API contract.
- `tests/test_management_api.py`, `tests/test_openapi.py`, and `tests/test_application_settings.py` — API and persistence behavior checks.

## Common failure modes and recovery actions

- **Failure:** Runtime route works but the contract test fails. **Recovery:** Compare `docs/openapi.json`, route registration, and compatibility redirects; update the intended contract and tests together.
- **Failure:** A setting appears in the UI but has no runtime effect. **Recovery:** Trace schema, validator, persistence, and runtime reader before documenting it as supported.
- **Failure:** A failed settings update changes stored state. **Recovery:** Keep validation before atomic persistence and add a regression test that checks state remains unchanged.
- **Failure:** An endpoint is accidentally public or rejects valid callers. **Recovery:** Verify which mode-specific token protects the route and add both authorized and unauthorized request tests.
- **Failure:** Environment and saved values disagree. **Recovery:** Follow the configuration precedence in `runtime_config.py` and cover the effective value in tests.

## Related Skills

- [`api-security-review`](../api-security-review/SKILL.md) — Review security-sensitive API and network changes.
- [`frontend-testing-linting`](../frontend-testing-linting/SKILL.md) — Validate browser clients that consume the API.
- [`documentation-build-validation`](../documentation-build-validation/SKILL.md) — Validate docs after changing API references.
- [`ci-quality-gates`](../ci-quality-gates/SKILL.md) — Run the broader local gate set.

## Maintenance notes

Review this skill when route versioning, authentication, settings precedence, schemas, or OpenAPI generation changes.
