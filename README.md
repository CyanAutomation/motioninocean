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

## Full Documentation

- Canonical deployment guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- Migration deltas only: [MIGRATION.md](MIGRATION.md)
- Container directory pattern specifics: [containers/README.md](containers/README.md)
