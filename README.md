# MotionInOcean 🌊📷

**Raspberry Pi Camera Streaming in Docker (Picamera2 / libcamera)**

MotionInOcean is a Docker-first project for running the **Raspberry Pi CSI camera** inside a container and streaming video across the network. It’s intended for **Raspberry Pi homelabs** and remote Docker hosts, where you want a reliable camera stream without installing a full stack directly on the host OS.

This repo is a fork of `hyzhak/pi-camera-in-docker`, with the goal of making the solution more polished and “homelab deployable”:

* build the image once
* publish to GHCR
* deploy from a `docker-compose.yml` that pulls an image tag (no local builds required)

---

## What this project is (and isn’t)

### ✅ What it is

* A lightweight container image that uses:

  * **Picamera2**
  * **libcamera**
  * Raspberry Pi OS Bookworm compatible packages
* Runs on Raspberry Pi 4/5 (ARM64) with CSI camera enabled
* Exposes an HTTP endpoint that provides camera streaming / frames
* Includes docker-compose examples for use on a remote host

### ❌ What it isn’t

* Not “Motion” (classic Motion daemon / motion.conf workflow)
* Not OctoPrint camera streaming (though it can be consumed by it)
* Not a full NVR / motion detection system (it’s a stream provider)

If you want motion detection / recording, use this project as a camera stream input to another service, or extend it.

---

## Why MotionInOcean exists

Running the Pi camera inside Docker is harder than USB webcams because the modern Raspberry Pi camera stack is built around **libcamera**, which relies on device discovery via udev and access to host hardware devices.

Many popular Docker camera images:

* don’t ship ARM64 builds
* or assume a traditional V4L2 webcam interface
* or require host-installed wrappers (e.g. `libcamerify`)

MotionInOcean solves this by building a container that installs and runs Picamera2 directly on top of Bookworm-compatible Raspberry Pi repositories.

---

## Architecture & key concepts

### Runtime model

* **Container** runs Python and Picamera2
* Uses host udev info to discover camera devices
* Requires elevated device access (see security model)

### Hardware access requirements

MotionInOcean uses:

* `/run/udev:/run/udev:ro` mounted into the container
* `privileged: true` by default for broad hardware/device access

These settings prioritize **reliability** over strict security hardening, which is reasonable for a homelab VLAN, but should not be exposed to the public internet.

---

## Quick start

### Requirements

* Raspberry Pi OS (64-bit) / Debian Bookworm ARM64
* Camera enabled and working on the host
* Docker + Docker Compose installed

Validate the host camera works before running containers, e.g.:

```bash
rpicam-hello
```

(or another libcamera test tool available on your OS).

---

## Deployment (recommended)

### Create project folder

```bash
mkdir -p ~/containers/motioninocean
cd ~/containers/motioninocean
```

### docker-compose.yml example

```yaml
services:
  motioninocean:
    image: ghcr.io/<your-org-or-user>/motioninocean:latest
    container_name: motioninocean
    restart: unless-stopped

    ports:
      - "8000:8000"

    environment:
      - TZ=Europe/London

    volumes:
      - /run/udev:/run/udev:ro

    privileged: true

    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

Start it:

```bash
docker compose up -d
docker logs -f motioninocean
```

---

## Image publishing & releases (GHCR)

MotionInOcean is designed so users can deploy without local builds.

### Release tags

* `latest` – most recent build
* `vX.Y.Z` – pinned releases

### CI/CD expectations

The repo is intended to include a GitHub Actions workflow that:

* builds the Docker image
* pushes to GHCR
* publishes ARM64 images by default

---

## Healthchecks

The container may optionally expose a lightweight healthcheck endpoint or respond at `/`.

For homelab-style “is it alive?” status in `docker ps`, we recommend:

* HTTP curl-based healthcheck *if the endpoint exists*, or
* TCP port open check if the service doesn’t provide a clean 200 response.

---

## Security notes

This container requires access to host camera devices.

The current default approach uses:

* `privileged: true`
* `/run/udev` mount

This is acceptable for trusted home networks, but should be hardened if used in more sensitive environments.

Future improvements should aim to reduce privilege by replacing privileged mode with explicit `devices:` mappings where possible.

---

# AI Agent Onboarding Guide

This section is aimed at AI coding agents or contributors.

## Goals for the fork

The fork exists to “productize” the original proof-of-concept:

1. Convert from `build:` compose workflows to publishable container images (`image:`)
2. Support homelab deployment patterns:

   * env files
   * logging rotation
   * healthchecks
3. Improve reliability on ARM64 Pi camera setups
4. Keep the stack lightweight and easy to reason about

---

## Code structure (expected)

Typical layout:

```
.
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── main.py / app.py (stream server)
└── .github/workflows/docker-publish.yml
```

---

## Development workflow

For local iteration:

```bash
docker compose build
docker compose up
```

For release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

---

## Suggested improvements backlog

Areas an AI agent can tackle:

### Reliability / Operations

* Improve startup logs and error output
* Add health endpoint (`/health`)
* Add structured logging
* Better config via env vars

### Security

* Replace privileged with explicit device mappings
* Document minimal required permissions
* Add “LAN-only” binding examples

### Performance

* configurable resolution / fps
* reduce CPU usage
* reduce latency
* optional hardware encoding support

### Usability

* provide “OctoPrint consumption” example
* provide “Home Assistant camera integration” example
* provide Homepage + Uptime Kuma config snippets

---

## Assumptions

* Primary deployment target is Raspberry Pi 4/5 running ARM64
* Service runs on private network only (home VLAN)
* Docker image tags should remain simple (`latest` supported)

---

## Support / debugging commands

Useful commands:

```bash
docker compose ps
docker compose logs -f
docker exec -it motioninocean bash
ls -l /dev/video*
```

