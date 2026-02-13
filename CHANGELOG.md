# Changelog

## Scope of this document

This file contains **user-visible product changes grouped by released version**.

- Release procedure and publishing automation live in [`docs/guides/RELEASE.md`](docs/guides/RELEASE.md).
- Test execution evidence and validation outputs live in [`docs/testing/README.md`](docs/testing/README.md).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.14.2] - 2026-02-13

- feat: enhance BASE_URL auto-detection for discovery announcements and update environment variable documentation
- fix: correct step numbering in deployment guide for webcam and management modes
- feat: add management and webcam mode configuration files with example settings
- refactor: improve test assertions and error messages in configuration validation tests
- feat: implement configuration validation and structured logging with rate limiting
- chore: remove .eslintignore and update package-lock.json for consistency

## [1.14.1] - 2026-02-13

- fix: update comments and assertions in test_announcer_retries_with_exponential_backoff for clarity
- test: add integration tests for webcam announce and discovery workflow
- fix: correct indentation in \_api_test_runtime_info function for proper error handling
- fix: correct indentation in parse_docker_url function for container ID validation
- fix: correct indentation in \_detect_camera_devices function for proper error handling
- refactor: simplify variable naming in test_run_webcam_mode_camera_detection_supports_both_global_camera_info_modes
- refactor: improve error handling and code readability across multiple files
- chore: clean up whitespace and formatting across multiple files
- chore: clean up whitespace and formatting across multiple files
- refactor: remove unused escapeHtml function and clean up device status handling
- Add VSCode extensions recommendations file
- Merge pull request #257 from CyanAutomation/codex/add-backend-tests-for-/api/config
- test: cover /api/config renderConfig contract in both modes

## [1.14.0] - 2026-02-13

- Merge pull request #256 from CyanAutomation/codex/extend-cors-config-handling
- Normalize CORS origins config in API and UI
- Merge pull request #255 from CyanAutomation/codex/update-url-validation-in-node_registry
- Merge pull request #254 from CyanAutomation/codex/remove-http-constraints-and-update-validation
- Merge pull request #253 from CyanAutomation/codex/derive-runtime-config-response-values
- Update main.py
- Update main.py
- Validate base_url schemes by transport and share docker URL parser
- Update node base URL validation by transport
- Derive /api/config runtime values from app state
- Merge pull request #252 from CyanAutomation/codex/update-api-config-route-to-return-fields
- Expand /api/config response for config UI

## [1.13.9] - 2026-02-13

- Merge pull request #251 from CyanAutomation/codex/update-refresh-click-handler-with-try/finally
- Merge pull request #250 from CyanAutomation/codex/replace-env-based-timeout-with-constant
- Ensure management refresh always restores polling interval
- Use fixed management API request timeout constant
- Merge pull request #249 from CyanAutomation/codex/refactor-announce-flow-and-implement-atomic-upsert
- Merge pull request #248 from CyanAutomation/codex/check-navigator.clipboard-before-writing
- Make discovery announce upsert atomic under registry lock
- Guard diagnostic clipboard writes when API is unavailable
- Merge pull request #247 from CyanAutomation/codex/extend-frontend-for-node-discovery-ux
- Merge pull request #246 from CyanAutomation/codex/add-unit-tests-and-update-documentation
- Add discovery metadata and approval UX for managed nodes
- Add management API test-mode coverage and operator docs
- Merge pull request #245 from CyanAutomation/codex/implement-ssrf-protections-for-proxying
- Merge pull request #244 from CyanAutomation/codex/modify-api-test-status-handling-in-webcam-app
- Merge pull request #243 from CyanAutomation/codex/github-mention-add-webcam-discovery-announcer-with-periodic
- Harden discovery private-IP registration policy
- Add injectable API status override for webcam test mode
- Fix discovery config validation and sanitize logged URLs
- Merge pull request #242 from CyanAutomation/codex/add-discovery-announcer-component-for-webcam-mode
- Update discovery.py
- Merge pull request #241 from CyanAutomation/codex/extend-webcam_action-for-new-api-commands
- Update webcam.py
- Add webcam discovery announcer with periodic announce loop
- Add api-test action controls to webcam endpoint
- Merge pull request #240 from CyanAutomation/codex/github-mention-codex-generated-pull-request
- Add regression tests for API test status edge cases
- Merge pull request #239 from CyanAutomation/codex/add-management-api-route-for-node-announcement
- Update pi_camera_in_docker/management_api.py
- Merge pull request #238 from CyanAutomation/codex/enhance-updatesetupui-for-device-statuses
- Merge branch 'main' into codex/enhance-updatesetupui-for-device-statuses
- Merge pull request #237 from CyanAutomation/codex/add-api-test-mode-support-to-webcam-app
- Update pi_camera_in_docker/shared.py
- Merge pull request #236 from CyanAutomation/codex/github-mention-codex-generated-pull-request
- Add authenticated discovery announce upsert endpoint
- Improve setup device detection UX and rescan flow
- Add API status test-mode scenario cycling
- Fix XSS risks in setup wizard HTML rendering
- Merge pull request #235 from CyanAutomation/codex/implement-stepper-setup-flow
- Update app.js
- Merge pull request #234 from CyanAutomation/codex/enforce-role-separation-in-documentation
- Merge pull request #233 from CyanAutomation/codex/create-prd-core.md-and-trim-prd-docs
- Add guided setup wizard with persisted stepper flow
- docs: enforce changelog/release/testing scope separation
- docs: split shared PRD context into core document
- Merge pull request #232 from CyanAutomation/codex/organize-documentation-structure-and-files
- docs: reorganize repository docs into guides reports and product
- Merge pull request #231 from CyanAutomation/codex/update-shutdown-behavior-for-camera-state
- Merge pull request #230 from CyanAutomation/codex/create-canonical-testing-documentation
- Merge pull request #229 from CyanAutomation/codex/refactor-documentation-to-centralize-deployment-guide
- Clear recording state immediately during shutdown
- docs: consolidate testing docs into canonical README
- docs: clarify doc ownership and centralize deployment guidance
- Update error codes in node status tests to reflect SSRF protection changes
- Fix error code in node status connectivity test from NODE_UNREACHABLE to NETWORK_UNREACHABLE
- Enhance request timeout configuration and diagnostics for network connectivity
- Add newline for improved readability in .env.example
- Remove deprecated environment and Docker Compose files for cleanup

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
