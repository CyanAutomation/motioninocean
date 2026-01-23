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
- Enhanced docker-compose.yml device mapping comments to clarify Pi model variations
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
