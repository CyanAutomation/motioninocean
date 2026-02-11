# Migration Guide: Docker Configuration

> **Latest Update:** February 11, 2026  
> **Breaking Changes:** v3 directory-based deployment, v2 environment variables  
> **Scope:** Docker Compose files, .env configuration, and authentication model

---

## v3: Directory-Based Deployment (Breaking Change)

**Status:** Released February 11, 2026 ✅

Motion In Ocean now uses **directory-based deployments** instead of custom-named compose files in the root. This improves tool compatibility (e.g., Dockhand, container managers) and provides clear isolation between deployments.

### What Changed

**Old Pattern (Deprecated):**
```
project root:
├── docker-compose.webcam.yaml       # Use with -f flag
├── docker-compose.management.yaml   # Use with -f flag  
├── docker-compose.hardened.yaml     # Use with -f flag
├── docker-compose.mock.yaml         # Use with -f flag
└── .env                             # Single .env
```

**New Pattern (Recommended):**
```
project root/containers/:
├── motioniocean-webcam/
│   ├── docker-compose.yml           # Standard filename, no -f needed
│   ├── docker-compose.hardened.yml  # Optional overlay, no -f confusion
│   ├── docker-compose.mock.yml      # Optional overlay for testing
│   └── .env
│
└── motioniocean-management/
    ├── docker-compose.yml           # Standard filename
    └── .env
```

### How to Migrate

#### 1. Copy the Deployment Directory

Choose the mode you need and copy it to your machine:

**For Webcam Mode (Camera Streaming):**
```bash
cp -r containers/motioniocean-webcam ~/containers/motioniocean-webcam
cd ~/containers/motioniocean-webcam
```

**For Management Mode (Node Hub):**
```bash
cp -r containers/motioniocean-management ~/containers/motioniocean-management
cd ~/containers/motioniocean-management
```

#### 2. Copy Your Existing Configuration

If you have an existing `.env` file from the old pattern:

```bash
cp ~/.env ~/containers/motioniocean-{mode}/.env
```

Or create a new one from the template:
```bash
cp .env.example .env
nano .env  # Review and customize if needed
```

#### 3. Start Using the New Pattern

**Old way (Deprecated):**
```bash
docker compose -f docker-compose.webcam.yaml up -d
```

**New way (Recommended):**
```bash
cd ~/containers/motioniocean-webcam
docker compose up -d
```

**No more `-f` flags needed!** Simply run `docker compose` from the deployment directory.

### Updating Scripts & Automation

If you have custom scripts or CI/CD pipelines using the old pattern:

**Old Pattern:**
```bash
docker compose -f docker-compose.webcam.yaml up -d
docker compose -f docker-compose.management.yaml up -d
```

**New Pattern:**
```bash
cd containers/motioniocean-webcam && docker compose up -d
cd containers/motioniocean-management && docker compose up -d
```

**Updated Repository Scripts:**

The repository scripts have been updated to support both patterns:

- **setup.sh** – Now detects deployment mode and guides setup
- **detect-devices.sh [directory]** – Now accepts target directory parameter
- **validate-deployment.sh [directory]** – Now validates a specific deployment

Usage:
```bash
cd ~/containers/motioniocean-webcam
/path/to/repo/setup.sh

/path/to/repo/detect-devices.sh .
/path/to/repo/validate-deployment.sh .
```

### Backward Compatibility & Timeline

- **Feb 11, 2026:** v3 released with directory-based structure and deprecation warnings
- **TBD:** Transition period where legacy root-level files still work but print deprecation notices
- **Future Release:** Legacy root-level files removed; directory-based is only option

**During the transition period:**
- ✅ Old files (`docker-compose.webcam.yaml`, etc.) still work with `-f` flags
- ✅ New directories (`containers/motioniocean-{mode}/`) are the recommended approach
- ⚠️ Old files print deprecation notices to encourage migration

---

## v2: Docker Configuration Simplification (Earlier Breaking Change)

> **Effective Date:** February 11, 2026
> **Type:** Clean break – environment variable schema redesign
> **Scope:** Docker Compose files, .env configuration, and authentication model

## Overview

The Motion In Ocean Docker configuration has been simplified to reduce complexity and align with the homelab appliance deployment model. This is a **breaking change** requiring migration of existing deployments.

### Key Changes at a Glance

| Aspect | Old | New |
|--------|-----|-----|
| **Compose Files** | Single `docker-compose.yaml` with device mappings | Separate `docker-compose.webcam.yaml`, `docker-compose.management.yaml` |
| **Device Access** | Explicit mappings + cgroup rules | `privileged: true` by default |
| **Environment Variables** | 20+ variables | 5 required variables |
| **Authentication** | `MANAGEMENT_AUTH_REQUIRED` boolean + token | Auth required only if token is non-empty |
| **Healthcheck** | Python script (`healthcheck.py`) | Simple curl HTTP check |

---

## Variable Migration

### Removed Variables

These variables are **no longer supported**. Remove them from your `.env` file:

| Old Variable | Replacement | Notes |
|--------------|-------------|-------|
| `MANAGEMENT_AUTH_REQUIRED` | Token-driven (see below) | Authentication is now implicit: if `MANAGEMENT_AUTH_TOKEN` is set, auth is required |
| `MOTION_IN_OCEAN_HEALTHCHECK_READY` | Removed | Healthcheck behavior is now consistent (`/health` for liveness) |
| `MOTION_IN_OCEAN_RESOLUTION` | Optional (advanced use only) | Not in minimal `.env.example`; still supported in code for power users |
| `MOTION_IN_OCEAN_FPS` | Optional (advanced use only) | Not in minimal `.env.example`; still supported in code for power users |
| `MOTION_IN_OCEAN_TARGET_FPS` | Optional (advanced use only) | Not in minimal `.env.example`; still supported in code for power users |
| `MOTION_IN_OCEAN_JPEG_QUALITY` | Optional (advanced use only) | Not in minimal `.env.example`; still supported in code for power users |
| `MOTION_IN_OCEAN_MAX_STREAM_CONNECTIONS` | Optional (advanced use only) | Not in minimal `.env.example`; still supported in code for power users |
| `MOTION_IN_OCEAN_PI3_PROFILE` | Optional (advanced use only) | Not in minimal `.env.example`; still supported in code for power users |
| `MOTION_IN_OCEAN_OCTOPRINT_COMPATIBILITY` | Optional (advanced use only) | Not in minimal `.env.example`; still supported in code for power users |
| `MOTION_IN_OCEAN_CORS_ORIGINS` | Optional (advanced use only) | Not in minimal `.env.example`; still supported in code for power users |
| `DOCKER_PROXY_PORT` | Removed | Use `MOTION_IN_OCEAN_PORT` for main service; docker-proxy is optional |
| `MOTION_IN_OCEAN_BIND_HOST` | Removed | Hardcoded to `127.0.0.1` by default; customize in compose file if needed |

### Required Variables (New Minimal Set)

Your `.env` file should now contain **only these variables**:

```bash
# Docker Image Tag
MOTION_IN_OCEAN_IMAGE_TAG=latest

# Web Server Port (default: 8000)
MOTION_IN_OCEAN_PORT=8000

# Timezone
TZ=Europe/London

# Deployment Mode: 'webcam' or 'management'
MOTION_IN_OCEAN_MODE=webcam

# Optional: Bearer token for authentication (leave empty to disable)
MANAGEMENT_AUTH_TOKEN=
```

### Optional Variables for Advanced Users

These variables are **still supported in the application** but are no longer documented in `.env.example`. They can be added back if you need to customize camera behavior:

- `MOTION_IN_OCEAN_RESOLUTION=1280x720`
- `MOTION_IN_OCEAN_FPS=30`
- `MOTION_IN_OCEAN_TARGET_FPS=` (empty to disable throttling)
- `MOTION_IN_OCEAN_JPEG_QUALITY=85`
- `MOTION_IN_OCEAN_MAX_STREAM_CONNECTIONS=4`
- `MOTION_IN_OCEAN_PI3_PROFILE=false`
- `MOTION_IN_OCEAN_OCTOPRINT_COMPATIBILITY=false`
- `MOTION_IN_OCEAN_CORS_ORIGINS=*`
- `MOCK_CAMERA=false`

**Note:** These variables are undocumented in standard deployment; they're provided for power users who need fine-grained control.

---

## Authentication Model Change

### Old Model

```bash
MANAGEMENT_AUTH_REQUIRED=true|false
MANAGEMENT_AUTH_TOKEN=<token-or-empty>
```

**Behavior:**
- If `MANAGEMENT_AUTH_REQUIRED=true` AND `MANAGEMENT_AUTH_TOKEN` is set → auth required
- If `MANAGEMENT_AUTH_REQUIRED=false` → auth disabled (regardless of token)

### New Model

```bash
MANAGEMENT_AUTH_TOKEN=<token-or-empty>
```

**Behavior:**
- If `MANAGEMENT_AUTH_TOKEN` is **empty** → authentication **disabled**
- If `MANAGEMENT_AUTH_TOKEN` is **non-empty** → authentication **required**

### Migration Path

| Old Config | New Config | Behavior |
|-----------|-----------|----------|
| `MANAGEMENT_AUTH_REQUIRED=false` + `MANAGEMENT_AUTH_TOKEN=` | `MANAGEMENT_AUTH_TOKEN=` | ✅ No change: auth disabled |
| `MANAGEMENT_AUTH_REQUIRED=false` + `MANAGEMENT_AUTH_TOKEN=secret123` | `MANAGEMENT_AUTH_TOKEN=secret123` | ✅ Auth enabled (secure) |
| `MANAGEMENT_AUTH_REQUIRED=true` + `MANAGEMENT_AUTH_TOKEN=secret123` | `MANAGEMENT_AUTH_TOKEN=secret123` | ✅ No change: auth enabled |
| `MANAGEMENT_AUTH_REQUIRED=true` + `MANAGEMENT_AUTH_TOKEN=` | `MANAGEMENT_AUTH_TOKEN=` | ✅ No change: auth disabled (fallback) |

---

## Compose File Migration

### Old Deployment

```bash
# Single unified service with devices always mounted
docker compose up
```

### New Deployment

#### Webcam Mode (Default)
```bash
# Simplified, homelab-friendly
docker compose -f docker-compose.webcam.yaml up
```

#### Management Mode
```bash
# Control plane for remote cameras
docker compose -f docker-compose.management.yaml up
```

#### Production with Explicit Device Mappings
```bash
# Uses hardened security posture
docker compose -f docker-compose.webcam.yaml -f docker-compose.hardened.yaml up
```

#### With Docker Socket Proxy
```bash
# Optional fine-grained Docker socket access control
docker compose -f docker-compose.webcam.yaml -f docker-compose.docker-proxy.yaml up
```

---

## Device Access Changes

### Old Model

Explicit device mappings in compose:
```yaml
devices:
  - /dev/dma_heap/system:/dev/dma_heap/system
  - /dev/vchiq:/dev/vchiq
  - /dev/video0:/dev/video0
  - /dev/v4l-subdev0:/dev/v4l-subdev0
  - /dev/media0:/dev/media0
  - /dev/media1:/dev/media1
  - /dev/dri:/dev/dri
device_cgroup_rules:
  - "c 253:* rmw"   # DMA heap
  - "c 511:* rmw"   # VCHIQ
  - "c 81:* rmw"    # Video devices
  - "c 250:* rmw"   # Media devices
```

### New Model (Default)

Simple `privileged: true` for homelab deployments:
```yaml
privileged: true
```

### New Model (Hardened)

For production environments, use `docker-compose.hardened.yaml` to restore explicit device mappings.

---

## Healthcheck Changes

### Old Model

```yaml
healthcheck:
  test: ["CMD", "python3", "/app/healthcheck.py"]
  interval: 2m
  timeout: 10s
  retries: 3
  start_period: 2m
```

Environment variable: `MOTION_IN_OCEAN_HEALTHCHECK_READY`

### New Model

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -fs http://localhost:8000/health || exit 1"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 30s
```

**Benefits:**
- No Python dependency in healthcheck
- More responsive (30s intervals vs 2m)
- Standard curl HTTP check (industry-standard)

---

## Step-by-Step Migration

### 1. Back Up Current Configuration

```bash
cp .env .env.backup
cp docker-compose.yaml docker-compose.yaml.backup
```

### 2. Update .env File

Start with `.env.example`:

```bash
cp .env.example .env
```

Then customize the 5 required variables:

```bash
# Edit .env and set:
MOTION_IN_OCEAN_IMAGE_TAG=latest
MOTION_IN_OCEAN_PORT=8000
TZ=Europe/London
MOTION_IN_OCEAN_MODE=webcam
MANAGEMENT_AUTH_TOKEN=            # Leave empty for localhost, set for remote access
```

**If you had camera customizations** (resolution, FPS, etc.), add them back to `.env`:

```bash
# Optional: Add if you need specific camera settings
MOTION_IN_OCEAN_RESOLUTION=1280x720
MOTION_IN_OCEAN_FPS=25
MOTION_IN_OCEAN_JPEG_QUALITY=80
```

### 3. Choose Your Deployment

**Webcam Mode (default):**
```bash
docker compose -f docker-compose.webcam.yaml up -d
```

**Management Mode:**
```bash
docker compose -f docker-compose.management.yaml up -d
```

**Production with Hardened Security:**
```bash
docker compose -f docker-compose.webcam.yaml -f docker-compose.hardened.yaml up -d
```

### 4. Verify Health Status

```bash
# Check container health
docker compose ps

# Check health endpoint directly
curl http://localhost:8000/health
```

### 5. Test Authentication (if token is set)

```bash
# If MANAGEMENT_AUTH_TOKEN is set:
export TOKEN="your-token-here"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/nodes
```

### 6. Clean Up Old Files (Optional)

Once verified, remove old compose configuration:

```bash
# Keep backup for reference
mv docker-compose.yaml.backup docker-compose.legacy.yaml

# Verify new files are in place
ls docker-compose.*.yaml
```

---

## Troubleshooting

### Container won't start: "python3: not found"

**Cause:** Old healthcheck.py still in use
**Solution:** Update compose file to use new HTTP healthcheck

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -fs http://localhost:8000/health || exit 1"]
```

### Authentication failing with old token structure

**Cause:** Old `MANAGEMENT_AUTH_REQUIRED=false` ignored token
**Solution:** Token now acts as both gate and key:
- If empty → no auth
- If set → auth required

```bash
# Update .env:
MANAGEMENT_AUTH_TOKEN=your-strong-random-token
```

### Device access denied errors

**Cause:** Using management mode but `privileged: true` expected
**Solution:** Use correct compose file for your deployment

```bash
# Webcam mode (needs device access):
docker compose -f docker-compose.webcam.yaml up

# Management mode (no device access needed):
docker compose -f docker-compose.management.yaml up
```

### Healthcheck unhealthy: timeout or connection refused

**Cause:** Container not responding on port 8000
**Solution:**
1. Verify port mapping: `docker ps | grep motion-in-ocean`
2. Check logs: `docker logs motion-in-ocean`
3. Verify `/health` endpoint exists: `curl -v http://localhost:8000/health`

---

## Summary

| Phase | Status | Impact |
|-------|--------|--------|
| **Environment Variables** | ✅ Simplified to 5 required + optional | Reduced config complexity by 80% |
| **Compose Files** | ✅ Split into mode-specific variants | Clearer intent; easier to reason about |
| **Device Access** | ✅ Privileged by default; hardened optional | Homelab-friendly; security still available |
| **Authentication** | ✅ Simplified token-driven model | Fewer decision points; more intuitive |
| **Healthcheck** | ✅ HTTP curl instead of Python | Standard practice; more responsive |

All functionality is preserved. The refactor is purely structural simplification for better maintainability and clarity.

For questions or issues, refer to [README.md](README.md) or [DEPLOYMENT.md](DEPLOYMENT.md).
