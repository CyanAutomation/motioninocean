# Changelog

## Scope of this document

This file contains **user-visible product changes grouped by released version**.

- Release procedure and publishing automation live in [`docs/guides/RELEASE.md`](docs/guides/RELEASE.md).
- Test execution evidence and validation outputs live in [`docs/testing/README.md`](docs/testing/README.md).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.20.2] - 2026-02-26

- Refactor code structure for improved readability and maintainability
- [webcam] Add utility modal and changelog card styles (#481)

## [1.20.1] - 2026-02-26

- [tests] Harden mock placeholder embedding and viewport bounds coverage (#480)
- [tests] Expand changelog API fallback and modal coverage (#479)
- [docs] Add /api/help/readme OpenAPI schemas and examples (#478)
- [webcam] Refactor mock stream placeholder embedding (#477)
- [webcam] Refactor help modal JSON response handling (#476)
- [webcam] Use API changelog link and improve degraded modal copy (#475)
- [webcam] Add remote changelog fallback and metadata (#474)
- [webcam] Bound mock stream placeholder overlay (#473)
- [webcam] Add resilient README help endpoint fallbacks (#472)
- [docker] Include changelog in runtime image and validate /api/changelog (#471)
- Refactor: Remove obsolete tests for management refresh and status handling; add new E2E tests for dashboard recovery and error display

## [1.20.0] - 2026-02-26

- Refactor: Improve assertion clarity in concurrency and changelog tests; remove unused imports in config validator tests
- Refactor: Remove obsolete tests for README help endpoint, DiscoveryAnnouncer, and banner output
- Refactor code for improved clarity and maintainability in discovery and test files
- Refactor test parameterization in Sentry integration tests for clarity and consistency

## [1.19.9] - 2026-02-26

- Enhance snapshot reliability under concurrent mutations with improved test assertions
- Enhance payload snapshot reliability with synchronized deepcopy and escalating retry delays
- Refactor code structure for improved readability and maintainability
- Enhance payload snapshot stability with retry logic and delays; update README test assertions for accuracy
- [webcam] Harden API test status scenario parsing (#470)
- [management] Clarify webcam token auth help text (#469)
- [settings] Reject unknown categories and fixed-schema keys in patches (#468)
- [build] Add git SHA provenance to image metadata and startup logs (#467)
- [tests] Add config validator import and disabled discovery coverage (#466)
- [lint] Fix Ruff issues and run Prettier (#465)
- [tests] Add targeted mock UI and frame generation coverage (#464)
- [webcam] Toggle mock placeholder visibility from runtime config (#463)
- [webcam] Add mock stream placeholder to index template (#462)
- [webcam] Render Mio SVG for mock stream frames (#461)
- [frontend] Remove duplicate fetchReadmeContent declaration (#460)
- [tests] Add README help endpoint and modal coverage (#459)
- Improve accessibility and visual details in SVG
- Create mio_floating.svg
- [webcam] Load README content in help modal (#458)
- [webcam] Add unauthenticated README help endpoint (#457)
- [ui] Limit changelog preview to three entries (#456)
- [webcam] Sanitize changelog unreadable-file response (#455)
- [webcam] Add rail help button modal handler (#454)
- [webcam] Add changelog API and modal rendering (#453)
- [config] Validate discovery management URL structure (#450)
- [webcam] Add reusable utility modal helpers (#452)
- [config] Validate discovery management URL structure (#451)
- [management] Support legacy private IP env fallback (#449)
- [webcam] Add changelog modal wiring and accessibility (#447)
- [discovery] Guard stop against self-join deadlock (#448)
- [discovery] Snapshot payload before announce serialization (#446)
- [management] Harden HTTP base_url transport validation (#445)
- fix: update file extensions from .yaml to .yml in README.md

## [1.19.8] - 2026-02-26

- [settings] Validate category object types in settings payload (#444)
- [sentry] Harden breadcrumb filter for missing fields (#443)
- [webcam] Fix missing closing brace in app.js cacheElements (#442)
- chore: automated code quality fixes [nightly] (#441)
- [sentry] Suppress stream aliases in traces sampler (#440)
- [discovery] Wake retry loop promptly on shutdown (#439)
- [management] Normalize malformed discovery metadata handling (#438)
- Add user and group configuration to docker-compose
- [runtime] Fix explicit env overlay precedence (#437)
- feat: add Motion In Ocean ASCII art to startup banner
- fix: update healthcheck command to use Python for improved reliability

## [1.19.7] - 2026-02-25

- docs: update OpenAPI specification with detailed descriptions and authentication mechanisms
- feat: add OpenAPI documentation file to Docker image
- docs: add API documentation endpoints to README and AGENTS.md
- fix: remove unused environment variable MIO_MOCK_CAMERA from tests

## [1.19.6] - 2026-02-25

- refactor: remove unused import of pytest in unit tests for banner
- fix: clean up comments and reformat environment variable section in .env.example
- fix: update docker-socket-proxy image tag and clean up environment variable comments
- feat: implement version reading from VERSION file and update startup banner
- feat: add startup banner with ASCII art and logging format options

## [1.19.5] - 2026-02-25

- fix: enhance error message for docker URL validation in test case
- style: format code for improved readability and consistency across multiple files
- fix: update ESLint ignores to include specific JS file and optimize ETag caching in settings API
- refactor: clean up formatting in deployment and migration guides, and streamline HTML button elements
- feat: enhance button transitions and improve settings section animations
- feat: implement Server-Sent Events for metrics streaming and optimize tab button handling
- feat: implement event delegation for input handling and enhance section toggle animations
- feat: add gzip compression and ETag caching for improved performance
- [management] Update interactivity tests for always-expanded sections and add webcam dataset version to test setup
- [refactor] Remove config group toggle functionality and associated styles
- [style] Add management side rail styles and update border-radius variables
- [design] Update curious, happy, and sleeping images in the mio theme
- [management] Preserve manual refresh unauthorized feedback (#436)
- [management] Prevent stale status restore after node deletion (#435)
- [runtime] Ensure env config overrides persisted settings (#434)
- [management] Reject unsupported transport in base URL validation (#433)
- [management] Allow discovery announce for mixed DNS results (#432)

## [1.19.4] - 2026-02-25

- [webcam] Split rail button layout from shared tab button (#431)
- [ui] Add WebKit webcam rail layout and theme regression test (#430)
- [ui] Refactor webcam rail colors to semantic tokens (#429)
- [management] Preserve discovery announce timestamps during approval (#428)
- [management] Harden docker URL parsing and encoding (#425)
- [management] Make discovery approval updates atomic (#426)
- [webcam] Refine side rail tab button layout (#427)
- [settings] Prevent patch validation from mutating live settings (#424)
- [runtime_config] Validate MIO_TARGET_FPS range with fps fallback (#423)
- [management] Harden upstream UTF-8 decode failures (#422)
- [setup] Align auth token env handling by app mode (#421)
- [discovery] Isolate announcer shutdown event lifecycle (#420)
- [runtime-config] Use validated port in default base URL (#419)
- [management] Make PUT webcam updates atomic with registry lock (#418)
- [docs] Align env variable docs to runtime-supported reads (#414)
- [config] Remove OctoPrint compatibility env warning aliases (#415)
- [config] Remove MIO_CORS_SUPPORT runtime mapping (#416)
- [runtime] Add explicit performance profile preset model (#417)
- chore: automated code quality fixes [nightly] (#413)

## [1.19.3] - 2026-02-24

- Various UI updates
- [docs] Align OctoPrint compatibility docs with always-on model (#412)
- [tests] Make OctoPrint /webcam compatibility tests always-on (#411)
- Refactor code structure for improved readability and maintainability
- Refactor HTML structure and improve accessibility in management template
- Refactor feature flags test to ensure fresh module imports and remove unused imports
- [config] Deprecate OctoPrint compatibility env control (#410)
- Enhance webcam layout and navigation styles for improved responsiveness and usability
- Add state and updateConnectionDisplays to test context for clearConfigDisplay
- Update test descriptions and refactor theme-related state handling in webcam-theme tests
- Refactor code structure for improved readability and maintainability
- [feature-flags] Remove OctoPrint compatibility toggle (#409)
- Refactor code structure and remove redundant sections for improved readability and maintainability
- [webcam] Always register OctoPrint compatibility routes (#408)
- Add OpenAPI specification for Motion In Ocean Management API
- [build] Simplify cloudbuild.yaml by removing GAR repository creation step and updating step descriptions
- [build] Ensure GAR repository exists before pushing image
- [build] Add cloudbuild.yaml for Google Cloud Build configuration
- [config] remove legacy env aliases for feature flags and private-ip override (#407)
- [config] Migrate CORS control to MIO_CORS_ORIGINS (#406)
- [webcam] Internalize pykms fallback and remove operator toggle (#405)
- [feature-flags] Add public metadata accessor for docs tests (#404)
- [docs] Align feature-flags guide with runtime registry (#403)
- [settings] Enforce environment-only runtime feature flags (#402)
- [feature-flags] Remove inert flags and enforce runtime usage (#401)
- [management] Make discovery announce upsert atomic (#400)
- [setup] Enforce fps range as 1..120 (#399)
- chore: automated code quality fixes [nightly] (#398)
- fix: update Dockerfile build args to use 'bookworm' suite and install picamera2 from apt repo
- Refactor code structure for improved readability and maintainability

- [webcam] OctoPrint compatibility is now always enabled in webcam mode and no longer controllable via feature flag/env toggle.
- [deprecation] `MIO_OCTOPRINT_COMPATIBILITY` and `OCTOPRINT_COMPATIBILITY` are deprecated, ignored at runtime, and emit warnings when set.
- [removal-plan] OctoPrint compatibility warning/compatibility shim is planned for removal in v1.21.0.
- [feature-flags] Active runtime feature-flag surface now excludes OctoPrint compatibility; mock camera remains the only active webcam-mode feature flag.

## [1.19.2] - 2026-02-23

- style: adjust z-index for video stream to ensure proper layering
- Refactor UI components and enhance styling for webcam application
- Refactor code structure for improved readability and maintainability
- docs: enhance README with updated requirements and quick start instructions

## [1.19.1] - 2026-02-23

- refactor: remove outdated Docker build instructions and clarify ARM64 build process
- docs: update README with ARM64 build instructions and cleanup
- feat: add Docker Hub support and update documentation for image registries
- refactor: consolidate and enhance CSS styles for improved layout and theming
- feat: enhance webcam stream interface with connection indicators and performance metrics

## [1.19.0] - 2026-02-23

- Add VSCode settings for Python environment management
- chore(deps): bump sentry-sdk[flask] from 2.19.0 to 2.53.0 (#397)
- chore(deps-dev): bump ruff from 0.15.1 to 0.15.2 (#396)
- chore(deps-dev): bump eslint from 10.0.0 to 10.0.1 (#395)
- chore(deps-dev): bump pytest-mock from 3.14.0 to 3.15.1 (#394)
- chore(deps): bump actions/setup-node from 5 to 6 (#393)
- [webcam] Tighten camera detection-path attribution (#391)
- [tests] Align camera info detection-path expectations (#390)
- chore: automated code quality fixes [nightly] (#392)
- [webcam] Move camera info probing to runtime (#389)

## [1.18.9] - 2026-02-22

- Rename SENTRY_DSN to MIO_SENTRY_DSN in documentation and code for consistency
- Enhance Sentry integration for error tracking across application components

## [1.18.8] - 2026-02-22

- Update libcamera validation in Dockerfile to check for CameraManager presence

## [1.18.7] - 2026-02-22

- Add libcap-dev to Dockerfile for enhanced capabilities

## [1.18.6] - 2026-02-22

- Update Dockerfile to install picamera2 in the virtual environment for arm64 builds

## [1.18.5] - 2026-02-22

- [docker] Update Raspberry Pi repository URLs and adjust Dockerfile test assertions for Trixie suite
- [build] Make Docker suite args explicit in Make targets (#388)

## [1.18.5] - 2026-02-22

- [docker] Base image stages on raspbian trixie slim (#387)
- [docker] Add arm64 camera install preflight diagnostics (#386)

## [1.18.4] - 2026-02-22

- Add .pth file to bridge Debian's dist-packages into venv for Python compatibility

## [1.18.3] - 2026-02-22

- Add Playwright CLI documentation and features for browser automation
- Remove rebranding scripts for node to webcam terminology
- [management] Reject non-object JSON from webcam proxies (#385)
- [runtime] Validate persisted camera fps range before merge (#384)
- [config] Validate MIO_FPS range in runtime camera config (#383)
- [management] Preserve discovery metadata on announce updates (#382)
- [shared] Standardize /health status as ok (#381)

## [1.18.2] - 2026-02-22

- [setup] Export MIO_APP_MODE in generated env (#380)
- [setup] Align auth token config key for env export (#379)
- [management] Unify private-IP SSRF flag evaluation (#378)
- [discovery] Avoid duplicate announce endpoint in management URL (#377)
- [management] Serialize node registry reads with lock (#376)
- [management] Canonicalize private IP override env var (#374)
- [setup] Use canonical management auth env key in setup output (#375)
- [management] Read private-IP policy dynamically per request (#373)
- [management] redact setup template auth token payload (#372)
- [runtime-config] Guard persisted merge values by type (#371)
- [cleanup] Remove CAT_GIF flag and cat-gif deployment artifacts (#370)
- [webcam] Remove cat gif refresh route and client call (#369)
- [tests] Canonicalize env-var fixtures and isolate legacy compat (#368)
- [webcam] Simplify mock frame initialization path (#367)
- [docs] Canonicalize env var naming across operator docs (#366)
- [runtime] Remove CATAAS env config from stream settings (#365)
- [containers] Switch cat-gif compose overlay docs/env to MIO keys (#364)
- [config] Deprecate legacy feature-flag aliases and expand Sentry redaction (#363)
- [config] Use canonical discovery env vars in validation hints (#362)
- [docker] Remove mock build-profile references and extend webcam fallback tests (#361)

## [1.18.1] - 2026-02-22

- [docker] Update Pillow requirement comments for unconditional install (#360)
- [webcam] Fallback to mock frames when real camera init fails (#359)
- [logging] Separate runtime mock camera from provenance metadata (#358)
- [docker] Always include mock-camera runtime dependency set (#357)

## [1.18.0] - 2026-02-22

- [camera] Prefer rpicam-hello before libcamera-hello in validation (#356)
- [docker] Use RPI_SUITE for Raspberry Pi apt source (#355)

## [1.17.9] - 2026-02-22

- [docker] Use dpkg architecture detection in arm64 conditionals (#354)
- [scripts] Detect stack architecture from container OS before env var (#353)
- Refactor type annotations for improved clarity in logging and management API
- Implement theme management and settings changes summary features

## [1.17.8] - 2026-02-21

- Enhance Dockerfile for architecture-aware Raspberry Pi camera package installation
- Update Docker build configuration to include mock camera for testing

## [1.17.7] - 2026-02-21

- Add architecture-aware stack validation script for motion-in-ocean
- Refactor Dockerfile to use build arguments for Debian suite; update logging configuration to handle picamera2 import gracefully

## [1.17.6] - 2026-02-21

- Enhance management UI with new navigation buttons and utility panel; update token handling description

## [1.17.5] - 2026-02-21

- [test] Update Dockerfile tests to reflect Debian Bookworm as primary suite
- [docker] Update Docker build configuration to use Debian Bookworm as primary suite

## [1.17.4] - 2026-02-21

- [docker] Fix active suite provenance metadata after fallback (#352)
- [build] Default RPI_SUITE to bookworm for docker targets (#351)
- [docker] Harden RPi suite update + fallback flow (#350)
- [docker] Reorder final-stage apt source setup for camera layer (#349)
- [ci] Decouple RPi suite from primary docker publish build (#348)

## [1.17.3] - 2026-02-21

- Enhance SKILL.md with container startup flow diagram and error message index; update Dockerfile and Makefile for improved build argument handling

## [1.17.2] - 2026-02-21

- Update SKILL.md and CONTRIBUTING.md for improved device mapping guidance and Docker build instructions
- Add ARM64 Docker build targets and update README for Raspberry Pi deployment
- Refactor Makefile and Python files for improved clarity and organization
- Refactor load_build_metadata to use pathlib for file handling
- Refactor file handling to use pathlib for improved path management
- Refactor code and documentation for clarity and consistency
- [docker] Fail fast when fallback preflight retry fails (#347)
- [docker] Add camera package preflight and fallback suite checks (#346)

## [1.17.1] - 2026-02-21

- [docs] Add canonical Docker build args and fallback guidance (#345)
- [docker] Align RPI_SUITE defaults to bookworm (#344)
- fix: remove duplicate MIO_APP_MODE assignment in .env.example

## [1.17.0] - 2026-02-21

- Implement feature X to enhance user experience and fix bug Y in module Z
- refactor: Update feature flag prefix from MOTION_IN_OCEAN to MIO for consistency
- Refactor environment variable prefixes from MOTION_IN_OCEAN to MIO
- Refactor environment variable names from MOTION_IN_OCEAN to MIO

## [1.16.9] - 2026-02-21

- Refactor test_env_example_contains_required_runtime_variables to remove unnecessary variables
- refactor: Update environment variable names for consistency across configurations and tests
- feat: Update environment variable names for consistency across tests
- Refactor environment variable names for consistency and clarity

## [1.16.8] - 2026-02-21

- feat: Enhance logging and provenance information in camera application
- feat: add dark variant gap report for management dashboard

## [1.16.7] - 2026-02-21

- Refactor code structure for improved readability and maintainability

## [1.16.6] - 2026-02-21

- docs: add troubleshooting section for camera detection issues in deployment guide
- Enhance Dockerfile and docker-compose configurations for improved camera support and security

## [1.16.5] - 2026-02-21

- Implement feature X to enhance user experience and fix bug Y in module Z
- chore: automated code quality fixes [nightly] (#343)
- Implement feature X to enhance user experience and fix bug Y in module Z
- Refactor Dockerfile healthcheck to use /health endpoint and update test assertions for thread lifecycle cleanup

## [1.16.4] - 2026-02-20

- Refactor healthcheck command to use Python socket connection for improved reliability
- Update CATAAS_API_URL to use the correct endpoint for cat GIFs
- Update comment formatting in .env.example

## [1.16.3] - 2026-02-20

- Add favicon and apple touch icons for improved branding
- [webcam] Degrade gracefully when no camera is available (#342)
- [webcam] Add configurable camera init failure strictness (#340)
- [webcam] Expose camera startup failure metadata in status endpoints (#339)
- [webcam] Generate correlation IDs when header is missing (#338)

## [1.16.2] - 2026-02-20

- [tests] Align Sentry init test with set_tag behavior (#337)
- chore(deps): bump flask in the pip group across 1 directory (#335)
- chore: automated code quality fixes [nightly] (#336)
- [runtime-config] Clarify CORS origins grouping and add networking tests (#334)
- [settings] Validate string pattern and URI formats (#333)
- [discovery] Make announcer restart-safe after stop (#332)
- [config] Align canonical camera FPS defaults across runtime/schema/api (#331)
- [observability] Set app_mode tag via Sentry scope API (#330)
- [tests] Update Sentry init assertions and app_mode tag coverage (#329)

## [1.16.1] - 2026-02-18

- Refactor webcam route handling with builder and handler patterns
- Implement API test mode functionality in webcam routes; validate interval parameter and manage state transitions
- Refactor logging statements across multiple modules to use parameterized formatting for improved performance and consistency
- Refactor validation functions in node_registry.py for improved clarity and modularity; streamline webcam validation logic in validate_webcam function
- Refactor logging statements to use parameterized formatting and ensure UTC timestamps in shared routes
- [api] Enhance management API with address resolution and vetting, add environment variable loading for settings

## [1.16.0] - 2026-02-18

- [webcam] Align discovery startup with webcam_id payload (#328)
- [auth] Separate webcam control-plane token from management token (#327)
- [settings] Harden JSON parsing in PATCH /api/settings (#326)
- Codex-generated pull request (#325)
- [management] Normalize overview availability for unsupported transports (#324)
- chore: automated code quality fixes [nightly] (#323)
- Fix a single test

## [1.15.9] - 2026-02-17

- Various fixes to management frontend
- [discovery] Preserve IPv6 netloc formatting in announce URL (#322)
- [management] Sanitize proxied Host header construction (#321)
- Small update to management.js
- refactor: Simplify concurrency tests and enhance feature flag API tests
- Various updates to tests
- refactor: Organize imports and enhance test assertions for settings changes
- refactor: Update environment variable handling in tests and improve validation for settings
- refactor: Enhance settings management and update test cases for improved validation

## [1.15.8] - 2026-02-17

- [discovery] Make announcer start/stop thread-safe (#320)
- refactor: Improve documentation formatting and update variable references in code
- [management] Keep allowed DNS resolutions when mixed with blocked IPs (#319)
- refactor: Update test cases to use management_api directly from client initialization
- fix: Add missing name field in package-lock.json
- refactor: Remove unused device security tests and streamline health endpoint checks

## [1.15.7] - 2026-02-17

- refactor: Add temporary application settings fixture and complete config dictionary for testing
- refactor: Simplify mock_path_exists function in unit tests for clarity
- refactor: Simplify mock_path_is_dir function in unit tests for clarity
- refactor: Add type ignore comments for type checking in Sentry initialization
- [refactor] Simplify return type casting in \_vet_resolved_addresses and \_request_json functions
- [refactor] Update variable name from "node_id" to "webcam_id" in create_webcam_app function
- [refactor] Improve code formatting and readability across multiple files
- [refactor] Update test to use "id" instead of "webcam_id" for webcam list response
- [refactor] Update API endpoint for node approval to use "webcams" instead of "nodes"

## [1.15.6] - 2026-02-17

- [refactor] Update environment variable references from "WEBCAM_DISCOVERY_SHARED_SECRET" to "NODE_DISCOVERY_SHARED_SECRET" in test cases
- [refactor] Update codebase to replace "node" references with "webcam" and improve error handling in various modules
- [refactor] Update references from "node" to "webcam" across codebase, including API endpoints, environment variables, and tests
- [refactor] Update references from "node" to "webcam" in environment variables, documentation, and codebase
- Refactor code structure for improved readability and maintainability
- [refactor] Replace validate_node with validate_webcam in FileWebcamRegistry methods and update test environment variable from DISCOVERY_NODE_ID to DISCOVERY_WEBCAM_ID
- [refactor] Update references from "node" to "webcam" in management API, registry, and migration scripts
- [refactor] Replace validate_node with validate_webcam in FileWebcamRegistry methods
- [refactor] Update references from "node" to "webcam" in management API and tests
- [refactor] Update "node_registry_path" to "webcam_registry_path" in configuration files
- [refactor] Optimize Dockerfile by copying GPG key and apt source list from builder stage
- [refactor] Rename "node" references to "webcam" in management API and node registry
- [refactor] Update terminology from "node" to "webcam" in management API and tests
- [refactor] Replace "node" terminology with "webcam" in registry and management API
- Rebrand "node" terminology to "webcam" throughout the project
- [feat] Add comprehensive rebrand script for node to webcam terminology
- [fix] Add missing camera runtime settings and update test configurations

## [1.15.5] - 2026-02-17

- [docs] Update README and .env.example files for configuration clarity and runtime settings management
- [ui] Enhance tab functionality and accessibility for settings panel
- Various updates to dependencies and package-lock.json
- [config] Update deployment configurations and package dependencies

## [1.15.4] - 2026-02-17

- Release v1.15.3
- [settings] Address review feedback on lock flow and init contract (#318)
- Codex-generated pull request (#317)
- [config] Add configurable application settings path (#316)
- [webcam] Tighten cat GIF retry reset and retry-time checks (#315)
- [containers] Fix /data ownership at startup before app launch (#314)
- [docker] Add CA certificates for CAT GIF HTTPS (#313)
- chore: automated code quality fixes [nightly] (#312)

## [1.15.3] - 2026-02-17

- No changes to log.

## [1.15.2] - 2026-02-16

- feat: add Sentry DSN configuration for error tracking in management and webcam services
- refactor: clean up imports and improve type hinting in Sentry configuration and tests
- fix: update Dockerfile user creation commands and adjust test assertions for runtime contract
- fix: update CORS options to include send_wildcard default and add type ignore for vetted_addresses
- Add parent-module and resolve-from packages with initial implementation
- Various update node packages
- feat: enhance documentation standards and add comprehensive examples for Python and JavaScript
- feat: add Sentry SDK for error tracking and APM
- docs: add documentation standards for Python and JavaScript functions
- refactor: enhance documentation structure and add Sphinx configuration for Python and JSDoc for JavaScript
- refactor: enhance documentation with detailed docstrings for node registry, runtime config, shared functions, and transport URL validation
- [config] Remove dead validator helpers and update coverage (#311)
- [runtime] Remove unused main \_load_advanced_config helper (#309)
- chore(deps-dev): bump ruff from 0.15.0 to 0.15.1 (#308)
- chore(deps-dev): bump eslint from 9.39.2 to 10.0.0 (#307)
- chore(deps): bump flask-limiter from 3.5.0 to 3.11.0 (#306)
- chore(deps): bump actions/setup-python from 5 to 6 (#305)
- [tests] Remove unused structured logging module coverage (#310)
- [management] Align form panel DOM ids with JS selectors (#304)
- [webcam] Add cat GIF fetch retry backoff (#303)
- chore: automated code quality fixes [nightly] (#302)
- [management] Stabilize collapsed form header toggle layout (#301)
- refactor: enhance documentation with detailed comments and JSDoc annotations across multiple JavaScript files

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
