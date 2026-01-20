# Changelog

All notable changes to motion-in-ocean will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
