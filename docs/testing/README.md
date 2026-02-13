# Testing Documentation (Canonical)

## Scope of this document
This file records **validation evidence and run outputs only**.

- Test/release procedures belong in [`docs/guides/RELEASE.md`](../guides/RELEASE.md) and developer workflow docs.
- User-facing release notes belong in [`CHANGELOG.md`](../../CHANGELOG.md).

## Latest validation summary
Consolidated from archived and legacy testing reports:
- Historical automated runs report passing unit, integration, and configuration suites.
- Parallel-container validation reports successful startup/health for webcam and management containers.
- A known/expected limitation remains: management-to-webcam status checks fail with `NODE_UNREACHABLE` when target addresses resolve to loopback/private ranges blocked by SSRF safeguards.

## Evidence sources
- Archive index: [`docs/testing/archive/`](archive/)
- Historical index snapshot: [`docs/testing/archive/TEST_DOCUMENTATION_INDEX-2026-02-11.md`](archive/TEST_DOCUMENTATION_INDEX-2026-02-11.md)
- Legacy reports retained for traceability under [`docs/reports/`](../reports/)

## Recorded outputs location
- CI logs and local terminal output generated during validation runs.
- Point-in-time markdown reports stored in [`docs/testing/archive/`](archive/).
