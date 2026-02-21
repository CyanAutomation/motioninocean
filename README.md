# motion-in-ocean 🌊📷

**Raspberry Pi CSI Camera Streaming in Docker (Picamera2 / libcamera)**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/CyanAutomation/motioninocean/workflows/CI%20-%20Test%20and%20Lint/badge.svg)](https://github.com/CyanAutomation/motioninocean/actions/workflows/ci.yaml)
[![Security Scan](https://github.com/CyanAutomation/motioninocean/workflows/Security%20-%20Docker%20Image%20Scan/badge.svg)](https://github.com/CyanAutomation/motioninocean/actions/workflows/security-scan.yaml)
[![Docker Image](https://img.shields.io/badge/GHCR-motion--in--ocean-informational)](https://github.com/CyanAutomation/motioninocean/pkgs/container/motioninocean)

> **Doc ownership**
>
> - **This file should contain:** a minimal quick-start and links to canonical docs.
> - **This file should not contain:** full deployment, migration, or container-pattern walkthroughs.

## Quick Start

```bash
cp -r containers/motioniocean-webcam ~/containers/motioniocean-webcam
cd ~/containers/motioniocean-webcam
cp .env.example .env
docker compose up -d
```

Open `http://localhost:8000`.

## Docker Build (Canonical Args)

### Primary Build (Stable)

When building manually, use the primary stable suite pairing:

```bash
docker build \
  --build-arg DEBIAN_SUITE=bookworm \
  --build-arg RPI_SUITE=bookworm \
  -t motion-in-ocean:local .
```

This is the recommended build configuration for all deployments, as of February 2026.

### Why Bookworm (Not Trixie)?

Debian 13 (Trixie, released 2026-02-01) enforces strict GPG policy: it rejects SHA1-based signature bindings as cryptographically insecure. The Raspberry Pi repository's signing key uses SHA1 binding signatures, so **Trixie cannot verify the RPi repository metadata**.

Bookworm (Debian 12) predates this policy change and remains compatible with the RPi repository. Once the Raspberry Pi project reissues their GPG key with modern signature algorithms, Trixie can be made the default again.

### Experimental: Build with Trixie

To test Trixie (may fail due to GPG policy):

```bash
make docker-build-trixie   # Experimental Trixie dev build
make docker-build-trixie-prod  # Experimental Trixie production build
```

## Building for Raspberry Pi (ARM64)

**Important:** Local `docker build` defaults to your host's CPU architecture:
- On ARM64 hosts (Linux ARM, Raspberry Pi itself) → builds ARM64 ✅
- On x86_64 hosts (Intel/AMD Mac, Linux x86) → builds x86, **won't work on Raspberry Pi** ❌

Raspberry Pi-specific camera packages (libcamera, picamera2) are ARM-only. If building on non-ARM hardware for Raspberry Pi deployment, explicitly target ARM64:

**Using Makefile (recommended):**
```bash
make docker-build-arm64       # Dev image with mock camera
make docker-build-prod-arm64  # Production image
```

**Using docker buildx directly:**
```bash
docker buildx build --platform linux/arm64 \
  --build-arg DEBIAN_SUITE=trixie \
  --build-arg RPI_SUITE=bookworm \
  -t motion-in-ocean:local .
```

**Note:** Multi-arch images (used in releases) are published with both `linux/arm64` and `linux/amd64` via CI automation; local builds default to your host architecture.

## Full Documentation

- Documentation hub: [docs/README.md](docs/README.md)
- Canonical deployment guide: [docs/guides/DEPLOYMENT.md](docs/guides/DEPLOYMENT.md)
- Migration deltas only: [docs/guides/MIGRATION.md](docs/guides/MIGRATION.md)
- Feature flags reference: [docs/guides/FEATURE_FLAGS.md](docs/guides/FEATURE_FLAGS.md)
- Container directory pattern specifics: [containers/README.md](containers/README.md)
