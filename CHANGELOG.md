# Changelog

## Scope of this document
This file contains **user-visible product changes grouped by released version**.

- Release procedure and publishing automation live in [`docs/guides/RELEASE.md`](docs/guides/RELEASE.md).
- Test execution evidence and validation outputs live in [`docs/testing/README.md`](docs/testing/README.md).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.13.8] - 2026-02-12

### Added
- Management-mode configuration files.
- SSRF protection diagnostics for management node connectivity.

## [1.13.7] - 2026-02-12

### Changed
- Management health checks now use a consistent `/api/status` contract.
- Management node status handling now surfaces clearer actionable guidance when nodes are unreachable.
- Management API auth coverage expanded for status checks.

## [1.13.6] - 2026-02-12

### Changed
- Management status aggregation now includes richer node failure details.
- Node request failures are normalized into clearer connectivity categories.
- Management UI styling tokens were consolidated for more consistent button/status presentation.

## [1.13.5] - 2026-02-11

### Changed
- Docker configuration and environment variable usage were simplified.

## [1.13.4] - 2026-02-11

### Added
- Bearer-token support for management API requests.
- Expanded test coverage and documentation for parallel container communication.

### Changed
- Management form validation now accepts HTTPS base URLs.
- Management refresh coordination improved to avoid overlapping status refreshes.
- Camera preflight diagnostics improved for missing or partial device-node setups.

## [1.13.3] - 2026-02-10

### Changed
- GPG key download flow hardened with improved retries and error handling.
- Python virtual environment bootstrap scripts improved.

## [1.13.2] - 2026-02-08

### Changed
- Camera detection tests were refactored for clearer behavior and fallback coverage.

## [1.13.1] - 2026-02-08

### Changed
- Management API auth model simplified to a bearer-token approach.
- Documentation updated to reflect bearer-token transport setup.

## [1.13.0] - 2026-02-08

### Added
- Persistent management-mode configuration storage.

### Changed
- Management startup, logging, and node-registry error handling improved.
- Camera device availability checks and related diagnostics improved.

## [1.12.9] - 2026-02-08

### Changed
- Management/node-request error messaging improved for clearer diagnostics.
- Validation and configuration error reporting standardized across key settings.

## [1.0.2] - 2026-01-21

### Fixed
- Prevented `PixelFormat`-related startup crashes when `pykms` is missing or incomplete.
- Expanded fallback handling for both import failures and incomplete module attributes.

### Changed
- Adopted a multi-stage Docker build to reduce runtime image size.
- Build-only dependencies moved out of the runtime image.

## [1.0.1] - 2026-01-19

### Fixed
- Added missing device mappings needed for libcamera camera enumeration on Raspberry Pi.
- Improved camera initialization reliability by aligning mapped device coverage with runtime needs.

### Documentation
- Clarified device-mapping guidance and hardware detection workflow.

## [1.0.0] - 2026-01-18

### Added
- Initial stable release of motion-in-ocean.
- Raspberry Pi camera streaming service with web UI, health checks, and metrics.
- Configurable camera runtime options (resolution, FPS, edge detection, timezone).
- Automated container build/publish workflow and deployment validation tooling.
- Comprehensive automated testing across unit, integration, and configuration paths.

### Security
- Non-privileged container defaults with explicit device access and `no-new-privileges`.
