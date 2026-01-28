# motion-in-ocean 🌊📷
**Raspberry Pi CSI Camera Streaming in Docker (Picamera2 / libcamera)**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/CyanAutomation/motioninocean/workflows/CI%20-%20Test%20and%20Lint/badge.svg)](https://github.com/CyanAutomation/motioninocean/actions/workflows/ci.yml)
[![Security Scan](https://github.com/CyanAutomation/motioninocean/workflows/Security%20-%20Docker%20Image%20Scan/badge.svg)](https://github.com/CyanAutomation/motioninocean/actions/workflows/security-scan.yml)
[![Docker Image](https://img.shields.io/badge/GHCR-motion--in--ocean-informational)](https://github.com/CyanAutomation/motioninocean/pkgs/container/motioninocean)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Status](https://img.shields.io/badge/status-alpha-orange)](#project-status)

motion-in-ocean is a **Docker-first** project for running a **Raspberry Pi CSI camera** inside a container and streaming video across the network. It’s intended for **Raspberry Pi homelabs** and remote Docker hosts, where you want a reliable camera stream without installing a full stack directly on the host OS.

This repo is a fork of `hyzhak/pi-camera-in-docker`, with the goal of making the solution more polished and **“homelab deployable”**:

- build the image once
- publish to GHCR
- deploy from a `docker-compose.yml` that pulls an image tag (no local builds required)

---

## Quick Start (Recommended)

> ✅ **Target:** Raspberry Pi OS (64-bit) / Debian Bookworm on ARM64  
> ✅ **Assumption:** CSI camera enabled and working on the host  
> ✅ **Usage:** Homelab LAN / VLAN only (do not expose directly to the internet)

### 1) Create folder + config

```bash
mkdir -p ~/containers/motion-in-ocean
cd ~/containers/motion-in-ocean

curl -fsSL https://raw.githubusercontent.com/<your-org-or-user>/motion-in-ocean/main/.env.example -o .env
nano .env
```

### 2) Create `docker-compose.yml`

```yaml
services:
  motion-in-ocean:
    image: ghcr.io/cyanautomation/motioninocean:latest
    container_name: motion-in-ocean
    restart: unless-stopped

    ports:
      - "127.0.0.1:8000:8000"  # localhost only (recommended)

    devices:
      - /dev/dma_heap:/dev/dma_heap
      - /dev/vchiq:/dev/vchiq
      # Add your /dev/video* and /dev/media* mappings based on your Pi hardware
      # Tip: use ./detect-devices.sh to identify devices reliably

    env_file:
      - .env

    volumes:
      - /run/udev:/run/udev:ro

    healthcheck:
      test: ["CMD", "python3", "/app/healthcheck.py"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### 3) Run it

```bash
docker compose up -d
docker logs -f motion-in-ocean
```

### 4) Check health

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

---

## What this project is (and isn’t)

### ✅ What it is

* A lightweight container image that uses:

  * **Picamera2**
  * **libcamera**
  * Raspberry Pi OS Bookworm compatible packages
* Runs on Raspberry Pi 3/4/5 (ARM64) with CSI camera enabled
* Exposes an HTTP endpoint that provides camera streaming / frames
* Includes docker-compose examples for use on remote host deployment patterns

### ❌ What it isn’t

* Not “Motion” (classic Motion daemon / motion.conf workflow)
* Not OctoPrint camera streaming (though it can be consumed by it)
* Not a full NVR / motion detection system (it’s a stream provider)

If you want motion detection / recording, use this project as a camera stream input to another service, or extend it.

---

## Why motion-in-ocean exists

Running the Pi camera inside Docker is harder than USB webcams because the modern Raspberry Pi camera stack is built around **libcamera**, which relies on device discovery via udev and access to host hardware devices.

Many popular Docker camera images:

* don’t ship ARM64 builds
* assume a traditional V4L2 webcam interface
* require host-installed wrappers (e.g. `libcamerify`)

motion-in-ocean solves this by building a container that installs and runs Picamera2 directly on top of Bookworm-compatible Raspberry Pi repositories.

---

## Project Status

This project is small and intentionally focused:

* ✅ solid “homelab” deployment baseline
* ✅ health endpoints
* ✅ Pi camera stack aligned with Bookworm
* 🔄 still evolving device detection, CI/CD and packaging polish

---

## Configuration

Create/edit `.env`:

```env
RESOLUTION=640x480
FPS=30
EDGE_DETECTION=false
MOTION_IN_OCEAN_CORS_ORIGINS=*
TZ=Europe/London
MOCK_CAMERA=false
```

### Options

* `RESOLUTION` - Camera resolution (e.g., `640x480`, `1280x720`, `1920x1080`). Max `4096x4096`.
* `FPS` - Frame rate limit. `0` uses camera default. Maximum recommended: `120`.
* `EDGE_DETECTION` - `true` enables Canny edge detection (CPU overhead).
* `MOTION_IN_OCEAN_CORS_ORIGINS` - Comma-separated list of allowed origins for CORS. If unset, defaults to `*` (all origins).
* `TZ` - Logging timezone.
* `MOCK_CAMERA` - `true` disables Picamera2 initialisation and streams dummy frames (dev/testing).

---

## Local Development (Non-Raspberry Pi)

For development/testing on a non-Raspberry Pi machine (e.g. `amd64` workstation), camera/display functionality won’t work due to hardware dependencies.

Use mock mode:

```env
MOCK_CAMERA=true
```

This allows you to validate:

* Flask server
* `/health` and `/ready`
* routing, config, general structure

---

## Building Custom Images

The Docker image comes in two variants optimized for different use cases:

### Minimal Image (Default, ~260MB)

The default build **excludes opencv-python-headless** to reduce image size by ~40MB and speed up downloads. Edge detection is disabled in this variant.

```bash
# Using Makefile
make docker-build

# Or directly with Docker
DOCKER_BUILDKIT=1 docker build -t motion-in-ocean:minimal .
```

### Full Image (With Edge Detection, ~300MB)

Include opencv-python-headless for edge detection support:

```bash
# Using Makefile
make docker-build-full

# Or directly with Docker
DOCKER_BUILDKIT=1 docker build --build-arg INCLUDE_OPENCV=true -t motion-in-ocean:full .
```

### Build Both Variants

```bash
make docker-build-both
```

### Image Size Comparison

| Variant | opencv-python-headless | Edge Detection | Compressed Size | Use Case |
|---------|------------------------|----------------|-----------------|----------|
| **Minimal** (default) | ❌ No | Disabled | ~260MB | Production deployments, faster pulls |
| **Full** | ✅ Yes | Available | ~300MB | When EDGE_DETECTION=true is needed |

**Note:** If you enable `EDGE_DETECTION=true` with the minimal image, the application will log a warning and continue without edge detection. Rebuild with `INCLUDE_OPENCV=true` to enable the feature.

---

## Architecture & key concepts

### Runtime model

* **Container** runs Python and Picamera2
* Uses host udev info to discover camera devices
* Requires elevated device access (see security model)

### Hardware access requirements

motion-in-ocean uses:

* `/run/udev:/run/udev:ro` mounted into the container
* Explicit device mappings (`/dev/dma_heap`, `/dev/video*`, `/dev/vchiq`, `/dev/media*`)

These settings prioritise **reliability** over strict hardening, which is reasonable for a homelab VLAN — but should not be exposed to the public internet.

---

## Healthchecks

The container exposes two endpoints:

* `/health` - Liveness (returns 200 if service is running)
* `/ready` - Readiness (returns 200 only if camera is initialised and streaming)

The docker-compose healthcheck uses the bundled `healthcheck.py`, which defaults to `/health`.
Override it with:

* `HEALTHCHECK_URL` (e.g., `http://127.0.0.1:8000/ready`)
* `HEALTHCHECK_TIMEOUT` (seconds, default `5`)

---

## Security Notes

This container requires access to host camera devices.

Recommended approach uses:

* explicit `devices:` mappings (not privileged mode)
* `/run/udev` mount (read-only)
* bind to localhost unless you *explicitly* need LAN access

### Network recommendations

* ✅ safest: `127.0.0.1:8000:8000`
* ⚠ LAN access: `8000:8000` (trusted networks only)
* ❌ avoid: internet exposure without authentication

If you need remote access, use a reverse proxy (nginx/Caddy/Traefik) with authentication.

---

## Technology Stack Verification (2026)

This project uses the **official modern Raspberry Pi camera stack**:

* **libcamera**
* **python3-libcamera**
* **Picamera2**
* **Debian Bookworm**
* **Python 3.11+**
* **libcap-dev** (required for python-prctl)

### Deprecated stack (not supported)

* ❌ picamera (v1.x)
* ❌ raspistill/raspivid
* ❌ MMAL

### Verification

```bash
rpicam-hello --version   # Should work on Bookworm
raspistill --help        # Command not found on Bookworm
```

**References**

* Picamera2 Manual (PDF): [https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)
* Camera Software Docs: [https://www.raspberrypi.com/documentation/computers/camera_software.html](https://www.raspberrypi.com/documentation/computers/camera_software.html)
* libcamera Project: [https://libcamera.org/](https://libcamera.org/)

---

## CI / CD

**Automated release process:**

Releases are **tag-driven** and fully automated:

1. Run `./create-release.sh` to create a new version
2. Script updates VERSION and CHANGELOG, commits, and pushes git tag
3. GitHub Actions automatically:
   - Builds Docker image for ARM64
   - Publishes to GHCR with version tags (`:vX.Y.Z`, `:X.Y.Z`, `:X.Y`, `:latest`)
   - Creates GitHub Release with changelog notes
4. Script verifies workflow completion and rolls back if it fails

**Continuous Integration:**

All pull requests and pushes to main/develop branches automatically run:

* **Test Suite** - Python 3.9, 3.11, and 3.12 compatibility tests
* **Linting** - Ruff code quality checks
* **Type Checking** - Mypy static type analysis
* **Security Scanning** - Bandit security checks and Trivy Docker scanning
* **Coverage Reporting** - Test coverage metrics with Codecov integration

**Docker images are published to:**

* `ghcr.io/cyanautomation/motioninocean:latest` (latest release)
* `ghcr.io/cyanautomation/motioninocean:vX.Y.Z` (specific version)
* `ghcr.io/cyanautomation/motioninocean:X.Y.Z` (semantic version)
* `ghcr.io/cyanautomation/motioninocean:X.Y` (major.minor)

**Key guarantees:**

* ✅ Every GitHub release has a corresponding Docker image
* ✅ `latest` tag always points to the newest release
* ✅ Failed builds trigger automatic rollback
* ✅ Release script waits for CI completion before finishing
* ✅ All PRs must pass CI checks before merging

See [RELEASE.md](RELEASE.md) for detailed release process documentation.

---

## Contributing

Contributions are welcome — even small ones like documentation tweaks.

### Quick Start for Contributors

This project now includes modern development tooling:

* **Pre-commit hooks** - Automatic code quality checks before commit
* **Makefile** - Convenient commands for common tasks (`make help`)
* **CI/CD** - Automated testing and linting on all PRs
* **Type checking** - Mypy for Python type safety
* **Security scanning** - Bandit and Trivy for vulnerability detection

**Getting started:**

```bash
# Clone and setup
git clone https://github.com/CyanAutomation/motioninocean.git
cd motioninocean
pip install -r requirements-dev.txt
make pre-commit

# View available commands
make help

# Run quality checks
make lint
make test
make ci
```

### Suggested contribution areas

* Pi device mapping detection improvements
* Compose examples for common homelab consumers (OctoPrint, Home Assistant)
* Prometheus metrics export
* Documentation improvements
* Bug fixes and testing

**See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.**

If you’d like to contribute:

1. Fork the repo
2. Create a feature branch
3. Open a PR

---

## Roadmap

Near-term:

* [x] GitHub Actions workflow for ARM64 builds to GHCR
* [x] Release tagging + Changelog automation
* [x] Automated GitHub Release creation
* [x] Pre-commit hooks for code quality
* [x] CI/CD pipeline (testing, linting, type checking)
* [x] Security scanning (Bandit, Trivy)
* [x] Dependabot for automated dependency updates
* [x] Multi-arch builds (ARM64 + AMD64 support)
* [ ] Home Assistant / OctoPrint examples
* [ ] Improve device mapping auto-detection tooling
* [ ] Prometheus metrics endpoint enhancements

---

## Support / Debugging

Common commands:

```bash
docker compose ps
docker compose logs -f
docker exec -it motion-in-ocean sh

ls -l /dev/video*
ls -l /dev/dma_heap
```

If something doesn’t work, open an issue and include:

* Pi model + OS version (Bookworm?)
* camera module type
* compose file snippet (devices/volumes)
* container logs
* output of `/health` and `/ready`

---

## License

This project should include a LICENSE file.

Until then: treat it as “all rights reserved”.

---

## Acknowledgements

This repo is a fork of `hyzhak/pi-camera-in-docker`, with a focus on making the concept more production-ready for homelab use.

---

## Links

* License section: [LICENSE](LICENSE.md)
* Contributing section: [CONTRIBUTING](CONTRIBUTING.md)
* Security section: [SECURITY](SECURITY.md)
* Code of Conduct: [CODE_OF_CONDUCT](CODE_OF_CONDUCT.md)
