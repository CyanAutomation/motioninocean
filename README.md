# motion-in-ocean 🌊📷

**Raspberry Pi CSI Camera Streaming in Docker (Picamera2 / libcamera)**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/CyanAutomation/motioninocean/workflows/CI%20-%20Test%20and%20Lint/badge.svg)](https://github.com/CyanAutomation/motioninocean/actions/workflows/ci.yaml)
[![Security Scan](https://github.com/CyanAutomation/motioninocean/workflows/Security%20-%20Docker%20Image%20Scan/badge.svg)](https://github.com/CyanAutomation/motioninocean/actions/workflows/security-scan.yaml)
[![Docker Image](https://img.shields.io/badge/GHCR-motion--in--ocean-informational)](https://github.com/CyanAutomation/motioninocean/pkgs/container/motioninocean)
[![Docker Hub](https://img.shields.io/docker/v/cyanautomation/motioninocean?label=Docker%20Hub&logo=docker)](https://hub.docker.com/r/cyanautomation/motioninocean)
[![GitHub Release](https://img.shields.io/github/v/release/CyanAutomation/motioninocean)](https://github.com/CyanAutomation/motioninocean/releases/latest)

## About

Motion In Ocean turns a Raspberry Pi CSI camera into a reliable, containerised MJPEG stream with a REST control plane. It runs in two modes:

- **Webcam mode** – captures frames via Picamera2/libcamera and streams them over HTTP (port 8000), with a REST API for settings and actions.
- **Management mode** – a hub (port 8001) that discovers and aggregates multiple webcam nodes, providing a single dashboard for multi-camera deployments.

Common integrations: [Home Assistant](https://www.home-assistant.io/), [OctoPrint](https://octoprint.org/), and any MJPEG-capable viewer.

## Requirements

| Requirement    | Minimum                                             |
| -------------- | --------------------------------------------------- |
| Raspberry Pi   | Pi 3B+ or newer (Pi 4 / Pi 5 recommended)           |
| OS             | Raspberry Pi OS Bookworm (64-bit)                   |
| Docker         | 24.0+                                               |
| Docker Compose | v2.20+                                              |
| Architecture   | `linux/arm64` (Pi) or `linux/amd64` (dev / testing) |

> Both `linux/arm64` and `linux/amd64` images are published. **Mock camera mode** works on any architecture without hardware.

## Quick Start

**Webcam mode (single camera):**

```bash
cp -r containers/motion-in-ocean-webcam ~/containers/motion-in-ocean-webcam
cd ~/containers/motion-in-ocean-webcam
cp .env.example .env
docker compose up -d
```

Open `http://localhost:8000`.

**Management mode (multi-camera hub):**

```bash
cp -r containers/motion-in-ocean-management ~/containers/motion-in-ocean-management
cd ~/containers/motion-in-ocean-management
cp .env.example .env
docker compose up -d
```

Open `http://localhost:8001`.

> No Raspberry Pi hardware? Use the mock camera overlay to try it out locally:
>
> ```bash
> docker compose -f docker-compose.yml -f docker-compose.mock.yml up -d
> ```

## Docker Images

Images are published to two registries on every release:

| Registry                         | Image                                  |
| -------------------------------- | -------------------------------------- |
| GitHub Container Registry (GHCR) | `ghcr.io/cyanautomation/motioninocean` |
| Docker Hub                       | `cyanautomation/motioninocean`         |

```bash
# Docker Hub (no authentication required)
docker pull cyanautomation/motioninocean:latest

# GitHub Container Registry
docker pull ghcr.io/cyanautomation/motioninocean:latest
```

Both registries publish the same multi-arch image (`linux/arm64`, `linux/amd64`) with identical tags (`latest`, `vX.Y.Z`, `X.Y.Z`, `X.Y`).

Motion In Ocean is locked to **Debian Bookworm**. No suite overrides are supported.

### Build Image

```bash
docker build -t motion-in-ocean:local .
```

### Build for Raspberry Pi (ARM64)

**Important:** Local `docker build` defaults to your host's CPU architecture:

- On ARM64 hosts (Linux ARM, Raspberry Pi itself) → builds ARM64 ✅
- On x86_64 hosts (Intel/AMD Mac, Linux x86) → builds x86, **won't work on Raspberry Pi** ❌

Raspberry Pi-specific camera packages (libcamera, picamera2) are ARM-only. If building on non-ARM hardware for Raspberry Pi deployment, explicitly target ARM64:

**Using Makefile (recommended):**

```bash
make docker-build-arm64       # ARM64 image (mock support included)
make docker-build-prod-arm64  # Production-tagged ARM64 image (same build profile)
```

**Using docker buildx directly:**

```bash
docker buildx build --platform linux/arm64 \
  -t motion-in-ocean:local .
```

**Note:** Multi-arch images (used in releases) are published with both `linux/arm64` and `linux/amd64` via CI automation; local builds default to your host architecture.

## Full Documentation

- Documentation hub: [docs/README.md](docs/README.md)
- Canonical deployment guide: [docs/guides/DEPLOYMENT.md](docs/guides/DEPLOYMENT.md)
- Migration deltas only: [docs/guides/MIGRATION.md](docs/guides/MIGRATION.md)
- Feature flags reference: [docs/guides/FEATURE_FLAGS.md](docs/guides/FEATURE_FLAGS.md)
- Container directory pattern specifics: [containers/README.md](containers/README.md)

## Environment Variables

Canonical app variables use the `MIO_*` prefix (e.g. `MIO_APP_MODE`, `MIO_PORT`, `MIO_BIND_HOST`). Legacy aliases (e.g. `APP_MODE`, `RESOLUTION`) are accepted temporarily during migration.

See the [deployment guide](docs/guides/DEPLOYMENT.md) for the full variable reference, legacy alias mapping, and migration examples.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a pull request, and review the [Code of Conduct](CODE_OF_CONDUCT.md). Run `make ci` to reproduce all CI checks locally before pushing.
