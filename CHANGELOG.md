# Changelog

All notable changes to motion-in-ocean will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-01-21

### Fixed
- Fixed `AttributeError: module 'kms' has no attribute 'PixelFormat'` crash when incomplete pykms package is installed
- Enhanced pykms workaround to catch both `ModuleNotFoundError` and `AttributeError`
- Added `PixelFormat` mock class with common pixel format attributes (RGB888, XRGB8888, BGR888, XBGR8888)
- Removed pykms installation from Dockerfile since DrmPreview functionality is not used in headless streaming mode
- Updated test coverage to verify both missing and incomplete pykms scenarios

### Changed
- Implemented multi-stage Docker build to reduce final image size by 80-150MB
- Moved build dependencies (gcc, python3-dev) to builder stage only
- Removed unused pytest-mock package from requirements-dev.txt
- Added missing PyYAML dependency to requirements-dev.txt (used by test files)

### Removed
- Removed unused pytest-mock==3.14.0 dependency (zero usage in codebase)
- Removed gcc and python3-dev from runtime Docker image (moved to builder stage)

## [1.0.1] - 2026-01-19

### Fixed
- Added missing `/dev/video18`, `/dev/video20-23`, and `/dev/video31` device mappings required for libcamera camera enumeration on Raspberry Pi 3A
- Fixed camera initialization failure (IndexError: list index out of range) caused by incomplete device access
- Improved `device_cgroup_rules` configuration with clarifying comments about automatic device access

### Documentation
- Enhanced docker-compose.yaml device mapping comments to clarify Pi model variations
- Updated README.md device configuration examples to include media controller devices
- Added note about running `detect-devices.sh` script for hardware-specific device detection

## [1.0.0] - 2026-01-18

### Added
- Initial stable release of motion-in-ocean
- Raspberry Pi camera streaming in Docker using Picamera2 and libcamera
- Support for Raspberry Pi 3/4/5 (ARM64) with CSI cameras
- Web interface for camera streaming at port 8000
- HTTP endpoints for health checks (`/health`) and metrics (`/metrics`)
- Flask-based web server with Motion JPEG streaming
- Edge detection support (configurable via environment variable)
- Mock camera mode for testing without hardware
- Docker Compose configuration with proper device access
- Device detection helper script (`detect-devices.sh`)
- Deployment validation script (`validate-deployment.sh`)
- Comprehensive test suite (configuration, integration, and unit tests)
- Support for modern libcamera stack (Debian Bookworm)
- Automatic device access via `device_cgroup_rules`
- Health checks with Docker healthcheck support
- Configurable resolution, FPS, and edge detection
- Timezone support via TZ environment variable

### Security
- Non-privileged container by default with explicit device access
- Security option `no-new-privileges:true` enabled
- Read-only udev mount for device discovery

### Documentation
- Comprehensive README with technology stack verification
- Pre-deployment validation commands
- Camera compatibility documentation (IMX219, Camera Module v2/v3)
- Performance recommendations for different Pi models
- Testing documentation (TEST_REPORT.md, TESTING_COMPLETE.md)

### Configuration
- Default configuration optimized for Pi 3 with IMX219 camera
- Resolution: 1640x1232 @ 30fps
- Support for /dev/dma_heap directory structure
- Support for multiple /dev/video* device nodes
- Configurable via environment variables in .env file

### Infrastructure
- GitHub Actions workflow for automated Docker image builds
- GHCR (GitHub Container Registry) publishing
- Multi-platform Docker build support (ARM64)
- Debian Bookworm-slim base image

## [Unreleased]

## [1.10.6] - 2026-01-29

- Merge pull request #101 from CyanAutomation/codex/update-dockerfile-to-clean-apt-lists
- Merge pull request #100 from CyanAutomation/codex/create-.dockerignore-with-exclusions
- Clean apt lists after installs
- Update .dockerignore
- Update .dockerignore
- Add dockerignore for local artifacts
- Enhance code quality and readability by refining import statements, improving error messages, and optimizing assertions across multiple test files.
- Refactor streaming logic for consistency and reliability
- Merge pull request #99 from CyanAutomation/copilot/fix-high-priority-bugs
- Fix linting issues - remove trailing whitespace
- Merge branch 'main' into copilot/fix-high-priority-bugs
- Add comprehensive concurrency tests covering race conditions and resource exhaustion
- Merge pull request #98 from CyanAutomation/copilot/fix-media-device-error
- Fix high-priority thread safety, timing, and resource management bugs
- Add test for camera detection error handling
- Add camera detection error handling to prevent IndexError
- Initial plan
- Initial plan
- Enhance device mapping validation and fix health endpoint metrics in tests

## [1.10.5] - 2026-01-28

- Enhance camera configuration and connection handling

## [1.10.4] - 2026-01-28

- Merge pull request #97 from CyanAutomation/codex/investigate-modulenotfounderror-in-docker
- Handle missing picamera2 array module

## [1.10.3] - 2026-01-28

- Add python3-numpy to Dockerfile for compatibility with simplejpeg and picamera2

## [1.10.2] - 2026-01-28

- Add NumPy dependency for array processing in requirements.txt

## [1.10.1] - 2026-01-28

- Merge pull request #96 from CyanAutomation/codex/github-mention-add-healthcheck_ready-toggle-for-healthcheck
- Clarify healthcheck fallback URL
- Merge pull request #95 from CyanAutomation/codex/add-environment-variable-for-health-check
- Merge pull request #94 from CyanAutomation/codex/update-streamstats-to-use-time.monotonic
- Add readiness toggle for healthcheck
- Use monotonic time for stream stats
- Merge pull request #93 from CyanAutomation/codex/add-device-mappings-to-motion-in-ocean-service
- Update docker-compose.yaml
- Merge pull request #90 from CyanAutomation/codex/refactor-test_healthcheck_url_validation
- Merge pull request #92 from CyanAutomation/codex/github-mention-reflect-camera-inactive/stale-state-in-conne
- Add explicit camera device mappings
- Merge pull request #91 from CyanAutomation/codex/update-test_dockerfile_has_flask-validation
- Update tests/test_units.py
- Fix connected state for stale streams
- Update Flask dependency test
- Fix healthcheck test setup
- Merge pull request #89 from CyanAutomation/codex/update-rendermetrics-connection-status
- Update pi_camera_in_docker/static/css/style.css
- Update pi_camera_in_docker/static/js/app.js
- Update camera status for stale streams
- Merge pull request #88 from CyanAutomation/codex/replace-hardcoded-jpeg-with-generated-jpeg-9kcq95
- Add Pillow fallback for mock camera JPEGs
- Merge pull request #87 from CyanAutomation/codex/update-fetchmetrics-to-use-abortcontroller-3wu4zf
- Handle metrics timeouts with abort
- Merge pull request #86 from CyanAutomation/codex/refactor-check_health-to-improve-hostname-validation
- Update tests/test_units.py
- Merge pull request #85 from CyanAutomation/codex/update-cors-variable-handling-in-app
- Fix healthcheck hostname validation
- Update CORS env handling
- Merge pull request #84 from CyanAutomation/codex/add-max_frame_age_seconds-to-metrics-response
- Add max frame age to metrics
- Merge pull request #83 from CyanAutomation/codex/refactor-updatestats-to-handle-errors
- Update pi_camera_in_docker/static/js/app.js
- Update pi_camera_in_docker/static/js/app.js
- Update pi_camera_in_docker/static/js/app.js
- Merge pull request #82 from CyanAutomation/codex/refactor-pi_camera_in_docker-mock-behavior
- Merge pull request #81 from CyanAutomation/codex/refactor-readiness-response-construction
- Simplify stats error handling
- Gate pykms mock behind env flag
- Refactor readiness response

## [1.0.9] - 2026-01-26

- Merge pull request #80 from CyanAutomation/codex/refactor-check_health-for-timeout-parsing
- Update healthcheck.py
- Update healthcheck.py
- Update healthcheck.py
- Merge pull request #79 from CyanAutomation/codex/refactor-camerastreamapp-to-module-functions
- Update pi_camera_in_docker/static/js/app.js
- Update pi_camera_in_docker/static/js/app.js
- Update pi_camera_in_docker/static/js/app.js
- Refine healthcheck validation flow
- Refactor camera app initialization
- Merge pull request #78 from CyanAutomation/codex/remove-_load_timeout-and-consolidate-parsing
- Merge pull request #77 from CyanAutomation/codex/refactor-streamingoutput-in-main.py
- Update pi_camera_in_docker/main.py
- Merge pull request #76 from CyanAutomation/codex/refactor-fetchmetrics-with-helper-function
- Remove unused healthcheck timeout helper
- Refactor streaming state
- Refactor metrics fetch timeout
- Merge pull request #75 from CyanAutomation/codex/refactor-updatestats-to-use-fetchmetrics-and-rendermetrics
- Merge pull request #74 from CyanAutomation/codex/refactor-/ready-route-payload-handling
- Update pi_camera_in_docker/main.py
- Refactor metrics polling helpers
- Refactor ready payload building
- Merge pull request #73 from CyanAutomation/codex/github-mention-drive-connection-status-from-/metrics-only
- Update connection status on stream events
- Merge pull request #72 from CyanAutomation/codex/remove-checkconnection-from-app.js
- Merge pull request #71 from CyanAutomation/codex/remove-stream-retry-logic-from-app.js
- Update pi_camera_in_docker/static/js/app.js
- Remove redundant connection check
- Simplify stream error handling
- Merge pull request #69 from CyanAutomation/codex/remove-generate_docker_compose_override-function
- Inline docker compose override generation
- Merge pull request #68 from CyanAutomation/codex/github-mention-harden-healthcheck_url-ssrf-validation
- Update healthcheck.py
- Fix healthcheck SSRF validation
- Merge pull request #67 from CyanAutomation/codex/remove-globals-and-simplify-error-handling
- Merge pull request #66 from CyanAutomation/codex/update-streamingoutput.get_status-implementation
- Merge pull request #65 from CyanAutomation/codex/inline-_load_timeout-logic-into-check_health
- Merge branch 'main' into codex/inline-_load_timeout-logic-into-check_health
- Simplify edge detection error logging
- Merge pull request #64 from CyanAutomation/codex/remove-calculatebackoffdelay-function
- Use get_fps in streaming status
- Merge pull request #63 from CyanAutomation/codex/github-mention-validate-healthcheck-url-scheme
- Update healthcheck.py
- Update healthcheck.py
- Update healthcheck.py
- Inline healthcheck timeout loading
- Simplify retry delay in camera app
- Harden healthcheck URL validation
- Merge pull request #62 from CyanAutomation/codex/update-dockerfile-for-correct-site-packages
- Update Dockerfile
- Update Dockerfile
- Update Dockerfile
- Merge pull request #61 from CyanAutomation/codex/replace-empty-string-checks-with-url-validation
- Update healthcheck.py
- Fix Python site-packages path in Dockerfile
- Validate healthcheck URL scheme
- Merge pull request #58 from CyanAutomation/codex/add-sigterm/sigint-handlers-in-main.py
- Update pi_camera_in_docker/main.py
- Update pi_camera_in_docker/main.py
- Merge pull request #59 from CyanAutomation/codex/update-updatestats-function-in-app.js
- Merge pull request #60 from CyanAutomation/codex/set-cors_origins-based-on-motion_in_ocean
- Merge pull request #57 from CyanAutomation/codex/add-aria-live-attribute-to-status-element
- Remove optional CORS env from compose
- Update stats fetch to metrics endpoint
- Handle shutdown signals for camera
- Add live region for connection status
- Merge pull request #50 from CyanAutomation/dependabot/pip/safety-3.7.0
- Merge pull request #48 from CyanAutomation/dependabot/github_actions/actions/setup-python-6
- Merge pull request #49 from CyanAutomation/dependabot/github_actions/actions/upload-artifact-6
- Merge pull request #51 from CyanAutomation/dependabot/pip/flask-3.1.2
- chore(deps): bump flask from 3.0.3 to 3.1.2
- Merge pull request #52 from CyanAutomation/dependabot/pip/pre-commit-4.3.0
- Merge pull request #53 from CyanAutomation/dependabot/docker/python-3.14-slim-bookworm
- Merge pull request #54 from CyanAutomation/dependabot/pip/flask-cors-6.0.2
- Merge pull request #55 from CyanAutomation/dependabot/pip/opencv-python-headless-4.13.0.90
- Merge pull request #56 from CyanAutomation/codex/add-module-level-lock-for-edge-detection
- Add lock for edge detection error tracking
- chore(deps): bump opencv-python-headless from 4.10.0.84 to 4.13.0.90
- chore(deps): bump flask-cors from 6.0.0 to 6.0.2
- chore(deps): bump python from 3.11-slim-bookworm to 3.14-slim-bookworm
- chore(deps-dev): bump pre-commit from 4.0.1 to 4.3.0
- chore(deps-dev): bump safety from 3.2.11 to 3.7.0
- chore(deps): bump actions/upload-artifact from 4 to 6
- chore(deps): bump actions/setup-python from 5 to 6
- Merge pull request #47 from CyanAutomation/codex/update-streamingoutput-methods-for-thread-safety
- Lock streaming metrics reads
- Merge pull request #46 from CyanAutomation/codex/modify-device-check-to-ignore-no-matches
- Update detect-devices.sh
- Merge pull request #45 from CyanAutomation/codex/remove-hardcoded-device-entries-from-docker-compose
- Update docker-compose.yaml
- Merge pull request #44 from CyanAutomation/codex/update-refreshstream-to-clear-streamretry
- Merge pull request #42 from CyanAutomation/codex/add-rate-limiter-to-edge-detection-logging
- Merge pull request #43 from CyanAutomation/codex/add-optional-environment-variables-for-healthcheck
- Update healthcheck.py
- Update main.py
- Avoid set -e failure on dma_heap listing
- Adjust device mappings for compose defaults
- Clear stream retry on manual refresh
- Add healthcheck env overrides
- Rate limit edge detection errors
- Merge pull request #41 from CyanAutomation/codex/locate-updatestats-and-modify-readiness-handling
- Merge pull request #40 from CyanAutomation/codex/fix-linting-in-main.py
- Resume stats polling after not ready
- Fix linting in camera main
- Merge pull request #39 from CyanAutomation/codex/locate-updatestats-and-modify-early-return
- Update pi_camera_in_docker/static/js/app.js
- Resume stats polling after not ready
- Merge pull request #38 from CyanAutomation/codex/add-cache-control-headers-to-routes
- Add no-store cache headers for health endpoints
- Merge pull request #37 from CyanAutomation/codex/fix-linting-errors-in-scripts
- Format Python files
- Merge pull request #35 from CyanAutomation/codex/create-prd-for-project-and-repository
- Merge pull request #36 from CyanAutomation/codex/update-index.html-and-app.js-for-new-stat-rows
- Add frame age stats to stream dashboard
- Add product requirements document
- Merge pull request #34 from CyanAutomation/codex/add-recording_started.clear-in-finally-block
- Clear recording flag on shutdown
- Merge pull request #33 from CyanAutomation/codex/change-early-return-on-503-in-updatestats
- Update pi_camera_in_docker/static/js/app.js
- Handle not ready stats response without backoff
- Merge pull request #32 from CyanAutomation/codex/update-connection-status-on-503-response
- Show ready reason while connecting
- Merge pull request #31 from CyanAutomation/codex/implement-timeout-logic-in-checkconnection
- Update pi_camera_in_docker/static/js/app.js
- Add timeout handling to connection check

## [1.0.8] - 2026-01-23

- Merge pull request #27 from CyanAutomation/codex/fix-python-linting-errors
- Merge pull request #30 from CyanAutomation/codex/github-mention-allow-python-3.11-slim-bookworm-as-acceptabl
- Update base image check patterns
- Merge pull request #29 from CyanAutomation/codex/update-base-image-policy-in-dockerfile
- Allow python base image in dockerfile test
- Merge pull request #28 from CyanAutomation/codex/handle-503-error-in-fetch-response
- Update pi_camera_in_docker/static/js/app.js
- Update pi_camera_in_docker/static/js/app.js
- Handle ready 503 status
- Fix lint exclusions and picamera imports
- Merge pull request #26 from CyanAutomation/codex/enhance-/ready-endpoint-for-frame-age-check
- Update pi_camera_in_docker/main.py
- Merge pull request #25 from CyanAutomation/codex/update-fetch-error-handling-for-readiness-check
- Update pi_camera_in_docker/static/js/app.js
- Add stale stream readiness check
- Handle not-ready status from /ready
- Merge pull request #24 from CyanAutomation/codex/update-streamingoutput.write-return-type
- Merge pull request #23 from CyanAutomation/codex/add-cors_origins-env-var-support
- Update pi_camera_in_docker/main.py
- Return byte count from streaming output write
- Merge pull request #22 from CyanAutomation/codex/update-dockerfile-to-copy-site-packages
- Add configurable CORS origins
- Update Dockerfile
- Merge pull request #21 from CyanAutomation/codex/move-picamera2-import-to-conditional
- Update pi_camera_in_docker/main.py
- Update Dockerfile package copy path
- Guard picamera2 imports for mock camera
- Merge pull request #20 from CyanAutomation/codex/fix-linting-errors-for-import-blocks
- Update node_modules/flatted/python/flatted.py
- Update node_modules/flatted/python/flatted.py
- Update node_modules/flatted/python/flatted.py
- Fix import spacing for lint

## [1.0.7] - 2026-01-22

- Merge pull request #19 from CyanAutomation/codex/augment-onstreamerror-with-refresh-backoff
- Update pi_camera_in_docker/static/js/app.js
- Add stream retry backoff
- Refactor healthcheck script and update error logging in test script
- Merge pull request #18 from CyanAutomation/codex/update-streamingoutput-for-last-frame-age
- Merge pull request #17 from CyanAutomation/codex/set-headers-for-/stream.mjpg-response
- Add last frame age to stream status
- Add no-cache headers to MJPEG stream
- Merge pull request #16 from CyanAutomation/codex/github-mention-handle-camera-stream-readiness-checks
- Avoid premature MJPEG stream termination
- Merge pull request #15 from CyanAutomation/codex/update-video_feed-to-check-recording_started
- Update pi_camera_in_docker/main.py
- Handle camera stream readiness
- Merge pull request #14 from CyanAutomation/codex/ensure-single-stats-fetch-at-a-time
- Update pi_camera_in_docker/static/js/app.js
- Prevent overlapping stats polling
- Merge pull request #13 from CyanAutomation/codex/update-updatestats-for-abortsignal.timeout
- Update pi_camera_in_docker/static/js/app.js
- Add timeout fallback for stats fetch
- Merge pull request #12 from CyanAutomation/codex/fix-linting-errors-and-formatting
- Fix lint issues in healthcheck and tests

## [1.0.6] - 2026-01-22

- Enhance Docker setup with conditional opencv installation and update documentation

## [1.0.5] - 2026-01-22

- Enhance Docker setup with healthcheck script and optimize dependencies

## [1.0.4] - 2026-01-21

- Update Dockerfile and requirements.txt to include python3-picamera2 and adjust comments
- Merge pull request #4 from CyanAutomation/dependabot/github_actions/github/codeql-action-4
- Merge pull request #6 from CyanAutomation/dependabot/github_actions/actions/checkout-6
- Merge pull request #5 from CyanAutomation/dependabot/pip/coverage-7.10.7
- Merge pull request #8 from CyanAutomation/dependabot/pip/mypy-1.19.1
- Merge pull request #7 from CyanAutomation/dependabot/github_actions/codecov/codecov-action-5
- Merge pull request #9 from CyanAutomation/dependabot/pip/bandit-1.8.6
- Merge pull request #10 from CyanAutomation/dependabot/pip/picamera2-0.3.33
- Merge pull request #11 from CyanAutomation/dependabot/pip/pytest-cov-7.0.0
- chore(deps-dev): bump pytest-cov from 6.0.0 to 7.0.0
- chore(deps): bump picamera2 from 0.3.18 to 0.3.33
- chore(deps-dev): bump bandit from 1.7.10 to 1.8.6
- chore(deps-dev): bump mypy from 1.13.0 to 1.19.1
- chore(deps): bump codecov/codecov-action from 4 to 5
- chore(deps): bump actions/checkout from 4 to 6
- chore(deps-dev): bump coverage from 7.6.9 to 7.10.7
- chore(deps): bump github/codeql-action from 3 to 4

## [1.0.3] - 2026-01-21

- feat: update changelog for version 1.0.2 with pykms enhancements and fixes fix: improve pykms import handling in main.py for better error management test: enhance test script to cover both ModuleNotFoundError and AttributeError scenarios for pykms
- feat: add markdownlint configuration file for linting Markdown files
- feat: add multi-architecture support for Docker builds and update README
- Merge pull request #1 from CyanAutomation/copilot/vscode-mknvjrml-3gos
- Merge pull request #3 from CyanAutomation/dependabot/pip/pip-8fb5dba437
- fix: make type checking non-blocking and update Makefile to focus on relevant directories
- fix: add explicit permissions to CI workflow for security best practices
- feat: code formatting, linting configuration, and documentation updates
- feat: add security, dependency management, and developer experience improvements
- feat: add development workflow automation (pre-commit, Makefile, CI)
- Bump flask-cors from 5.0.0 to 6.0.0 in the pip group across 1 directory
- Checkpoint from VS Code for cloud agent session
- Refactor Dockerfile and Python code for improved dependency management and type annotations

## [0.7.4] - 2026-01-21

- Add pykms support and import fallback in headless environments

## [0.7.3] - 2026-01-20

- Update permissions in Docker publish workflow to allow write access for contents

## [0.7.2] - 2026-01-20

- Fix heredoc syntax in release notes generation and ensure variable replacements are correctly applied

## [0.7.1] - 2026-01-20

- Enhance GitHub Actions workflow for Docker image release: extract and validate changelog, improve release notes generation, and add error handling.

## [0.7.0] - 2026-01-20

- Implement automated release process with GitHub Actions workflow and rollback functionality

## [0.6.4] - 2026-01-20

- Remove test_metrics_endpoint.py as it is no longer needed
- Add /metrics endpoint for camera metrics and implement integration tests
- Enhance error handling in CameraStreamApp with exponential backoff for retrying stats updates

## [0.6.3] - 2026-01-20

- Remove motion-in-ocean-logs.txt due to obsolete log data
- Update Dockerfile to include flask-cors and enhance create-release.sh for changelog generation
- Enhance configuration and installation scripts; improve camera streaming logic

## [0.6.2] - 2026-01-20

### Changed
- Release version 0.6.2


## [0.6.1] - 2026-01-20

### Changed
- Release version 0.6.1


## [0.6.0] - 2026-01-20

### Changed
- Release version 0.6.0


### Planned
- Multi-camera support
- Long-running stability improvements
- Thermal throttling detection and handling
- Prometheus metrics export
- Remote logging integration
- Camera hotplug support

[1.0.0]: https://github.com/cyanautomation/motioninocean/releases/tag/v1.0.0
