---
name: api-security-review
description: Review changes to management API authentication, remote-node requests, discovery, or credential handling. Use when a change can affect SSRF protections, authorization boundaries, or exposure of tokens and sensitive data.
owner: motion-in-ocean team
last-reviewed: 2026-11-15
category: Development
compatible-repo-areas:
  - pi_camera_in_docker/management_api.py
  - pi_camera_in_docker/transport_url_validation.py
  - pi_camera_in_docker/discovery.py
  - docs/guides/DEPLOYMENT.md
  - tests/test_management_api.py
  - tests/test_discovery.py
---

## Purpose

Preserve the management hub's authentication and outbound-request boundaries when changing APIs that communicate with discovered or configured webcam nodes.

## Scope and trigger conditions

- Use when changing management or webcam token checks, node discovery, node URL validation, remote status/action requests, or credential storage and logging.
- Use [`backend-api-settings`](../backend-api-settings/SKILL.md) for general API and settings contract changes without a security-boundary impact.
- Use [`ci-triage`](../ci-triage/SKILL.md) to investigate CodeQL or Trivy findings; this skill reviews design and behavior, not scanner configuration.

## Required inputs

- The proposed change and affected routes, modes, or remote request flows.
- Relevant authentication configuration, URL validation code, tests, and deployment guidance.
- Any security finding or threat assumption that prompted the change.

## Step-by-step workflow

1. Trace data from request input or discovery announcement to storage and any outbound network call. Identify who controls each URL, token, and payload.
2. Confirm the correct mode-specific bearer token protects each privileged route. Check missing, malformed, and incorrect credentials; avoid logging token values.
3. For outbound URLs, preserve HTTP/HTTPS shape validation and the resolved-address policy. Check loopback, link-local, private, reserved, and cloud metadata destinations against the intended `MIO_ALLOW_PRIVATE_IPS` behavior.
4. Verify DNS resolution is checked at the connection boundary and that redirects or alternate address forms cannot bypass the policy. Keep the policy enforced for each remote request, not just when a node is first registered.
5. Review discovery announcement authentication, approval flow, and stored node credentials. Ensure sensitive values do not appear in API responses, logs, diagnostics, or error details.
6. Add or update focused tests for allowed and blocked destinations, authentication outcomes, and secret redaction. Use the existing management and discovery test fixtures rather than reaching external hosts.
7. Run focused tests and inspect scanner results when available:

   ```bash
   .venv/bin/python -m pytest tests/test_management_api.py tests/test_discovery.py -q
   ```

8. Compare the result with [`docs/guides/DEPLOYMENT.md`](../../../docs/guides/DEPLOYMENT.md) and explain any intentional policy change and its operator impact in the pull request.

## Validation checklist

- [ ] Privileged routes reject missing and invalid bearer tokens.
- [ ] Remote destinations are validated at the point of use and DNS results follow the configured policy.
- [ ] Private-address exceptions are explicit, documented, and tested.
- [ ] Discovery cannot silently bypass authentication or approval requirements.
- [ ] Credentials are not exposed in responses, logs, diagnostics, or test output.
- [ ] Focused tests cover both rejected and permitted cases.
- [ ] Deployment security guidance matches the implementation.

## Source of truth

- `pi_camera_in_docker/management_api.py` — Route authorization, destination screening, and remote-node calls.
- `pi_camera_in_docker/transport_url_validation.py` — URL shape and transport validation.
- `pi_camera_in_docker/discovery.py` — Discovery announcement behavior.
- `docs/guides/DEPLOYMENT.md` — Tokens, SSRF protections, private-address policy, and deployment boundaries.
- `tests/test_management_api.py` and `tests/test_discovery.py` — Security-sensitive behavior and regression coverage.
- `.github/workflows/codeql.yml` and `.github/workflows/security-scan.yml` — Automated code and image scanning.

## Common failure modes and recovery actions

- **Failure:** A host is validated at registration but resolves differently later. **Recovery:** Enforce address validation at connection time and test DNS changes with controlled fixtures.
- **Failure:** A private node is blocked in a trusted LAN deployment. **Recovery:** Check the explicit `MIO_ALLOW_PRIVATE_IPS` setting and its documented network trust implications; do not remove URL validation globally.
- **Failure:** A token appears in a diagnostic or exception. **Recovery:** Redact it at the logging/serialization boundary and add a regression assertion.
- **Failure:** A scanner finding has no obvious local reproduction. **Recovery:** Follow the tainted input to the sink, inspect the relevant control and test, then document evidence before changing or suppressing the finding.
- **Failure:** A security fix breaks normal node operations. **Recovery:** Add tests for safe public and intended private-node cases, then rerun the management API suite.

## Related Skills

- [`backend-api-settings`](../backend-api-settings/SKILL.md) — Maintain API and settings contracts.
- [`ci-triage`](../ci-triage/SKILL.md) — Diagnose CodeQL, Trivy, and other CI findings.
- [`deployment-validation-health-checks`](../deployment-validation-health-checks/SKILL.md) — Validate deployment health and authentication configuration.

## Maintenance notes

Review this skill when management authentication, discovery, outbound HTTP handling, URL validation, or deployment security policy changes.
