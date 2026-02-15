# Changelog

## Scope of this document

This file contains **user-visible product changes grouped by released version**.

- Release procedure and publishing automation live in [`docs/guides/RELEASE.md`](docs/guides/RELEASE.md).
- Test execution evidence and validation outputs live in [`docs/testing/README.md`](docs/testing/README.md).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.15.1] - 2026-02-15

- refactor: update Dockerfile to copy full application code and set PYTHONPATH for module execution
- refactor: enhance documentation with detailed docstrings for various functions and tests
- refactor: enhance documentation with detailed docstrings for webcam mode and management scripts
- refactor: enhance documentation with detailed docstrings across multiple files
- refactor: enhance documentation and improve test coverage for camera streaming functionality
- refactor: rename test functions and classes for consistency and clarity

## [1.15.0] - 2026-02-15

- refactor: update file paths and improve type hinting for clarity

## [1.14.9] - 2026-02-15

- Refactor debug logging in test_config.py; adjust stderr output and frame timing logic
- General fixes
- Enhance FrameBuffer logging for dropped frames and normalize action values in webcam routes; update FPS assertion in tests
- Improve frame dropping logic in FrameBuffer to include next valid capture time in debug logging
- docs: align management status polling diagram with per-node status endpoint (#299)
- Improve frame dropping logic in FrameBuffer to include debug logging
- Adjust sleep duration in tests and fix formatting in route iteration
- docs: align management probe diagrams with /api/status contract (#298)
- docs: add auth boundary sequence diagram for deployment (#297)
- Refactor management client initialization to return client and additional context
- Enhance resolution parsing and update networking config loading

## [1.14.8] - 2026-02-15

- Harden settings load path against concurrent file changes (#294)
- Use configured CORS origins in middleware (#293)
- Handle invalid feature flag maps in settings loading/diff (#292)
- Make frame selection resilient to frame list size changes (#291)
- Use relative settings schema import in config validator (#290)
- Refactor frame generation to fetch outside generator lock (#289)
- Codex-generated pull request (#288)
- Handle malformed numeric env values in settings changes (#287)
- Unify runtime settings merge contract for settings API (#286)
- Reload persisted settings after patch save (#285)
- Fix settings changes resolution parsing and add endpoint tests (#284)
- Make application settings mutations atomic under lock (#283)
- Preserve HTTPS hostname for TLS while pinning vetted node IPs (#282)

## [1.14.7] - 2026-02-15

- chore: Update VERSION to 1.14.6 and correct CHANGELOG path in release script
- chore: Bump version to 1.14.5
- fix: Clear recording_started state in app initialization for consistent test behavior
- fix: Adjust sleep duration in FrameBuffer write loop for accurate target FPS
- refactor: Update device pattern display in availability check and clean up test assertions
- refactor: Update device availability checks and mock path methods in unit tests
- refactor: Update glob pattern to use absolute path and adjust management API import
- feat: Implement Pi3 profile defaults and update import paths for management API
- refactor: Update import statements to use package-relative paths in integration and management tests
- feat: Add health, readiness, and metrics endpoints to the main application
- refactor: Update import statements to use package-relative paths for consistency across modules and tests
- refactor: Improve error handling in subprocess calls and update test assertions for clarity
- refactor: Update module imports to use package-relative paths in test files
- refactor: Update import statements for consistency and clarity across test files
- refactor: Update import statements to use package-relative paths in test files
- refactor: Update import statements to use package-relative paths for consistency across test files
- refactor: Enhance directory creation in ApplicationSettings and add CAT_GIF feature flag
- refactor: Update import statements to use package-relative paths for better module resolution
- refactor: Update import paths for pi_camera_in_docker and enhance module loading in tests
- refactor: Add conditional import for picamera2 and enhance test skipping logic
- refactor: Update docker-compose and environment file paths in configuration tests
- refactor: Update Flask app initialization function parameter for clarity
- refactor: Clean up whitespace in configuration validation and settings API files
- Enhance runtime settings documentation and improve UI/UX
- refactor: Improve Flask app initialization and middleware registration
- feat: Refactor configuration loading into separate functions for camera, stream, and discovery settings
- Add health indicator rendering in config panel (#281)
- refactor: Improve error handling and validation messages in ApplicationSettings
- Add scripts for device detection, health checks, and deployment validation
- feat: Enhance ApplicationSettings with version validation and error handling
- feat: Implement settings management UI and persistence tests
- feat: Add new docker-compose configurations for management, webcam, and mock camera modes
- feat: Add settings management API and application settings persistence

## [1.14.4] - 2026-02-15

- feat: Implement cat GIF generator and refresh API
- Add Cat GIF generator and integrate into mock camera mode
- Remove backup pre-commit configuration file
- Add pre-commit configuration for code quality and consistency
- Fix pre-commit issues
- Add health check section to config panel (#280)
- Merge pull request #279 from CyanAutomation/codex/extend-ui-context-and-add-tests
- Merge pull request #278 from CyanAutomation/codex/add-health_check-to-json-response
- Add advanced diagnostics toggle coverage in frontend tests
- Add health_check indicators to /api/config response
- Merge pull request #277 from CyanAutomation/codex/add-styles-for-diagnostic-control-row
- Refine diagnostics toggle layout and collapsed panel styling
- Merge pull request #276 from CyanAutomation/codex/add-advanced-checkbox-functionality
- Update management.js
- Sync advanced diagnostics panel visibility and focus behavior
- Merge pull request #275 from CyanAutomation/codex/add-frontend-test-for-management-panel-toggle
- Update management-panel-collapse.test.mjs
- Update management-panel-collapse.test.mjs
- Merge pull request #274 from CyanAutomation/codex/update-tests-and-documentation-for-new-ux
- Merge pull request #273 from CyanAutomation/codex/add-advanced-checkbox-and-diagnostics-container
- Update management.js
- Update management.html
- Add VM-based test for management panel collapse toggle
- Align config QA checks/docs with 3-section UX
- Add advanced toggle for diagnostic panel visibility
- Merge pull request #272 from CyanAutomation/codex/update-/api/config-response-structure
- Merge pull request #271 from CyanAutomation/codex/add-toggle-functionality-to-management.js
- Remove limits from /api/config response
- Add collapsible node form panel state handling
- Merge pull request #270 from CyanAutomation/codex/github-mention-codex-generated-pull-request
- Merge pull request #269 from CyanAutomation/codex/update-renderconfig-to-remove-limits
- Fix mobile node form display conflict
- Remove limits rendering from config panel
- Merge pull request #268 from CyanAutomation/codex/update-management.css-for-collapsed-layout
- Merge pull request #267 from CyanAutomation/codex/remove-system-limits-config-group
- Refine management form panel collapsed rail styling
- Remove System Limits group from configuration panel
- Merge pull request #266 from CyanAutomation/codex/github-mention-add-accessible-toggle-header-wrapper-for-nod
- Update management.js
- Add node form panel toggle behavior in management UI
- Merge pull request #265 from CyanAutomation/codex/edit-management.html-for-panel-enhancements
- Add collapsible header structure for node form panel
- Enhance PRD documentation with detailed architecture and state machine diagrams for backend and frontend components

- api: remove deprecated `limits` object from `/api/config` response

## [1.14.3] - 2026-02-14

- Merge pull request #264 from CyanAutomation/codex/add-frontend-tests-for-showdiagnosticresults
- Merge pull request #263 from CyanAutomation/codex/add-frontend-test-for-startconfigpolling
- Expand diagnostic panel frontend coverage and accessibility
- Add frontend test coverage for config polling interval
- Merge pull request #262 from CyanAutomation/codex/update-config-panel-footer-text
- Update config panel auto-update interval text to 5 seconds
- Merge pull request #261 from CyanAutomation/codex/implement-diagnostic-results-summary-banner
- Add diagnostic summary banner with remediation CTAs
- Merge pull request #260 from CyanAutomation/codex/update-polling-interval-to-5000-ms
- Increase config polling interval to 5s
- Merge pull request #259 from CyanAutomation/codex/extend-diagnose-payload-in-management_api
- Add structured diagnose statuses and severity-driven UI rendering
- Merge pull request #258 from CyanAutomation/codex/add-diagnostics-section-to-management-page
- Add structured diagnostics panel for node management

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
