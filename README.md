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
* Runs on Raspberry Pi 3/4/5 (ARM64) with CSI camera enabled
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

## Technology Stack Verification (2026)

This project uses the **official and current** Raspberry Pi camera stack:

- **libcamera** - Official camera subsystem (Bookworm standard since 2022)
- **Picamera2** - Official Python library maintained by Raspberry Pi Foundation
- **Debian Bookworm** - Latest stable Raspberry Pi OS base (ARM64)
- **Python 3.11+** - Modern Python with proper async and type support

### What We're NOT Using (Deprecated)

- ❌ **picamera (v1.x)** - Deprecated library, only works with legacy camera stack
- ❌ **raspistill/raspivid** - Command-line tools removed in Bookworm
- ❌ **MMAL** - Legacy Multimedia Abstraction Layer, replaced by libcamera

### Why This Matters

The Raspberry Pi camera ecosystem changed significantly with Raspberry Pi OS Bullseye (2021) and continues in Bookworm (2023+):

- **Legacy stack** (MMAL/raspistill) is no longer maintained or available
- **Modern stack** (libcamera/picamera2) is required for Camera Module v3, HQ Camera, and future hardware
- **Hardware ISP** acceleration only available through libcamera
- All official Raspberry Pi documentation recommends this approach

### Verification

If you're unsure whether your host system uses the modern stack, check:

```bash
# Modern stack (✓ Correct)
rpicam-hello --version   # Should work on Bookworm

# Legacy stack (✗ Won't work on Bookworm)
raspistill --help        # Command not found on Bookworm
```

**Official References:**
- [Picamera2 Manual (PDF)](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)
- [Raspberry Pi Camera Software Documentation](https://www.raspberrypi.com/documentation/computers/camera_software.html)
- [libcamera Project](https://libcamera.org/)

---

## Architecture & key concepts

### Runtime model

* **Container** runs Python and Picamera2
* Uses host udev info to discover camera devices
* Requires elevated device access (see security model)

### Hardware access requirements

MotionInOcean uses:

* `/run/udev:/run/udev:ro` mounted into the container
* Explicit device mappings (e.g., `/dev/dma_heap`, `/dev/video*`, `/dev/vchiq`) are used for hardware/device access.

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

### Configure environment variables

Create a `.env` file with your desired configuration:

```bash
cp .env.example .env
nano .env  # Edit as needed
```

Or create `.env` manually with your preferred settings:

```bash
cat > .env << 'EOF'
RESOLUTION=640x480
FPS=30
EDGE_DETECTION=false
TZ=Europe/London
EOF
```

**Configuration options:**

* `RESOLUTION` - Camera resolution (e.g., `640x480`, `1280x720`, `1920x1080`). Maximum `4096x4096`.
* `FPS` - Frame rate limit. `0` uses camera default. Maximum recommended: `120`.
* `EDGE_DETECTION` - Set to `true` to enable Canny edge detection (adds CPU overhead).
* `TZ` - Timezone for logging timestamps (e.g., `America/New_York`, `Asia/Tokyo`).

### docker-compose.yml example

```yaml
services:
  motioninocean:
    image: ghcr.io/<your-org-or-user>/motioninocean:latest
    container_name: motioninocean
    restart: unless-stopped

    ports:
      - "8000:8000"  # Accessible on all network interfaces

    devices:
      # These device mappings are for camera access.
      # The /dev/video* paths might change across reboots or different RPi models.
      # /dev/dma_heap is essential for libcamera, used by picamera2 on modern Raspberry Pi OS.
      - /dev/dma_heap
      - /dev/vchiq
      - /dev/video0
      - /dev/video10
      - /dev/video11
      - /dev/video12

    env_file:
      - .env  # See .env.example for configuration options

    volumes:
      - /run/udev:/run/udev:ro

    deploy:
      resources:
        limits:
          memory: 512M  # Appropriate for Raspberry Pi 4
          cpus: '1.0'
        reservations:
          memory: 256M
          cpus: '0.5'

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3

    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

**Network access notes:**

* The service binds to `0.0.0.0:8000` and is accessible on your local network
* For localhost-only access, change port mapping to `"127.0.0.1:8000:8000"`
* **Security:** Do not expose port 8000 to the internet without authentication
* Consider using a reverse proxy (nginx, Caddy) with authentication for remote access

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

The repo has future intent, to include a GitHub Actions workflow that:

* builds the Docker image
* pushes to GHCR
* publishes ARM64 images by default

---

## Healthchecks

The container exposes two health endpoints:

* `/health` - Basic liveness check (returns 200 if service is running)
* `/ready` - Readiness check (returns 200 only if camera is initialized and streaming)

The docker-compose configuration includes a healthcheck that monitors the `/health` endpoint. Container status will show as "healthy" or "unhealthy" in `docker ps` output.

To manually check health status:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

---

## Security notes

This container requires access to host camera devices.

The recommended approach uses:

* Explicit `devices:` mappings (not privileged mode)
* `/run/udev` mount (read-only)

**Important security considerations:**

* The service binds to all network interfaces (`0.0.0.0:8000`) for homelab access
* Suitable for trusted home networks behind a firewall
* **Do not** expose directly to the internet without authentication
* Consider using a reverse proxy with authentication for remote access
* The container runs with minimal privileges and only requires camera device access

For maximum security on localhost-only setups, change the port binding in docker-compose.yml to:
```yaml
ports:
  - "127.0.0.1:8000:8000"
```

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

Areas for future enhancements:

### ✅ Completed

* ✅ Add health endpoint (`/health` and `/ready`)
* ✅ Add structured logging  
* ✅ Better config via env vars with validation
* ✅ Configurable resolution and FPS
* ✅ Document minimal required permissions
* ✅ Add resource limits for Raspberry Pi deployment
* ✅ Reduce CPU usage via `pre_callback` for edge detection

### 🔄 Future Work

#### Performance

* Optional hardware encoding support (H.264/H.265)
* Reduce latency for real-time applications
* Multi-camera support (CAMERA_INDEX env var)

#### Usability

* Provide "OctoPrint consumption" example
* Provide "Home Assistant camera integration" example
* Provide Homepage + Uptime Kuma config snippets
* Add Prometheus metrics export for monitoring
* Add basic authentication option

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
ls -l /dev/dma_heap
```

