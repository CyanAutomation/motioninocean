# Motion In Ocean - Container Deployment Patterns

> **Doc ownership**
>
> - **This file should contain:** container directory layout, compose overlay patterns, and repository-specific container composition conventions.
> - **This file should not contain:** generic startup, environment-variable walkthroughs, or full deployment runbooks duplicated from root docs.

## Purpose of `containers/`

This directory defines the **deployment packaging pattern** used by Motion In Ocean:

- One deployment per directory
- Standard `docker-compose.yml` entrypoint in each deployment
- Optional overlays for specialized behavior
- Clear separation between webcam and management roles

## Container Registry

Images are published to both registries on every release tag:

| Registry | Image |
| --- | --- |
| GitHub Container Registry (default) | `ghcr.io/cyanautomation/motioninocean` |
| Docker Hub | `cyanautomation/motioninocean` |

The compose files default to GHCR. To use Docker Hub instead, override `MIO_IMAGE_TAG` and change the `image:` value in your local copy:

```yaml
image: cyanautomation/motioninocean:${MIO_IMAGE_TAG:-latest}
```

## Directory Pattern

```
containers/
├── motioniocean-webcam/
│   ├── docker-compose.yml
│   ├── docker-compose.hardened.yml
│   ├── docker-compose.mock.yml
│   └── .env.example
│
├── motioniocean-management/
│   ├── docker-compose.yml
│   └── .env.example
│
└── shared/
```

## Overlay Conventions

### Webcam Base

- `motioniocean-webcam/docker-compose.yml` is the base streaming deployment.

### Hardened Overlay

- `motioniocean-webcam/docker-compose.hardened.yml` is layered on top of webcam base for stricter device/security posture.
- Intended to be combined with host-specific device mapping workflows.

### Mock Overlay

- `motioniocean-webcam/docker-compose.mock.yml` is layered on top of webcam base for hardware-free validation/testing.

### Management Base

- `motioniocean-management/docker-compose.yml` is the management/control-plane deployment.

## Composition Examples (Pattern-Only)

```bash
# Base webcam
cd containers/motioniocean-webcam && docker compose up -d

# Webcam + hardened overlay
cd containers/motioniocean-webcam && docker compose -f docker-compose.yml -f docker-compose.hardened.yml up -d

# Webcam + mock overlay
cd containers/motioniocean-webcam && docker compose -f docker-compose.yml -f docker-compose.mock.yml up -d
```

## Canonical App Vars vs Docker/Compose Keys

- **Canonical app env vars:** `MIO_*` (for example: `MIO_APP_MODE`, `MIO_PORT`, `MIO_BIND_HOST`).
- **Standard Docker/Compose keys (not app env vars):** `image`, `ports`, `environment`, `volumes`, `networks`, `depends_on`, `restart`.

### Legacy aliases still accepted temporarily

| Canonical `MIO_*` var       | Legacy alias                           |
| --------------------------- | -------------------------------------- |
| `MIO_APP_MODE`              | `APP_MODE`, `MOTION_IN_OCEAN_MODE`     |
| `MIO_PORT`                  | `MOTION_IN_OCEAN_PORT`                 |
| `MIO_BIND_HOST`             | `MOTION_IN_OCEAN_BIND_HOST`            |
| `MIO_RESOLUTION`            | `RESOLUTION`, `MOTION_IN_OCEAN_RESOLUTION` |
| `MIO_MANAGEMENT_AUTH_TOKEN` | `MANAGEMENT_AUTH_TOKEN`                |
| `MIO_DISCOVERY_TOKEN`       | `DISCOVERY_TOKEN`                      |

## Configuration Model: Infrastructure vs. Runtime Settings

**Motion In Ocean separates configuration into two distinct categories:**

### Infrastructure Configuration (Environment Variables in docker-compose/.env)

These settings control deployment and system behavior, and are set at container startup. They **cannot** be modified via the web UI.

**Webcam mode:**

- `MIO_PORT`, `MIO_BIND_HOST` — Network binding
- `MIO_MOCK_CAMERA` — Mock camera for testing
- `MIO_PI3_PROFILE` — Hardware profile
- OctoPrint compatibility is always enabled in webcam mode; `MIO_OCTOPRINT_COMPATIBILITY` and `OCTOPRINT_COMPATIBILITY` are deprecated/ignored.
- `MIO_MANAGEMENT_AUTH_TOKEN` — Security token for management hub access
- `APPLICATION_SETTINGS_PATH`, `NODE_REGISTRY_PATH` — Persistence locations
- `MIO_SENTRY_DSN` — Error tracking
- `LIMITER_STORAGE_URI` — Advanced system settings

**Management mode:**

- Same network, persistence, and system settings as webcam
- Plus: `NODE_DISCOVERY_SHARED_SECRET`, `MIO_ALLOW_PRIVATE_IPS` — Discovery security
- Plus: `DOCKER_PROXY_PORT` — Docker transport support

See [.env](motion-in-ocean-webcam/.env) and [.env.example](motion-in-ocean-webcam/.env.example) for complete documentation of each variable.

### Runtime Settings (Web UI, persisted to /data/application-settings.json)

These settings control camera behavior, logging, discovery, and feature flags. They are managed exclusively through the web UI at runtime and **do not require container restart**.

**Available categories:**

1. **Camera Settings** — Resolution, FPS, JPEG quality, stream connections, frame age
2. **Logging Settings** — Log level, format, identifier inclusion
3. **Discovery Settings** — Enable/disable, management URL, token, interval
4. **Feature Flags** — Performance optimization, debugging, observability, integrations

**Access and manage settings:**

- Webcam UI: `http://localhost:8000/api/settings/schema`
- Management UI: `http://localhost:8001/api/settings/schema`
- Persistent storage: `/data/application-settings.json` (JSON file, readable/editable)

**Precedence order:**

1. **Highest:** Persisted settings in `/data/application-settings.json` (set via UI)
2. **Middle:** Environment variables (`.env` or docker-compose)
3. **Lowest:** Hardcoded application defaults (in source code)

### Example: Starting a New Deployment

```bash
# 1. Start docker-compose with infrastructure variables
# (Only environment-level configuration; set BIND_HOST, PORT, MOCK_CAMERA, etc.)
docker compose up -d

# 2. Open web UI
# Webcam: http://localhost:8000
# Management: http://localhost:8001

# 3. Configure runtime settings via UI
# - Set camera resolution, FPS, quality
# - Configure logging level
# - Enable discovery and features as needed
# Settings persist to /data/application-settings.json

# 4. Settings are immediately active; no restart needed
```

### Benefits of This Separation

- **Infrastructure as Code**: Docker-compose files declare only deployment/system concerns
- **Runtime Flexibility**: Operators can tune camera/logging settings without restarting
- **Persistence**: UI changes survive container restarts
- **Clarity**: Environment variables are no longer a catch-all for every setting
- **Security**: Infrastructure secrets (tokens) are kept separate from runtime tuning

### Migration Note for Existing Deployments

If you have environment variables set in `.env` for camera settings (for example `MIO_RESOLUTION`, `MIO_FPS`) or feature flags:

1. Remove them from your `.env` file (recommended)
2. Start the container normally
3. Use the web UI to configure camera, logging, and feature flag settings
4. The newly persisted settings file (`/data/application-settings.json`) will take precedence

Old environment variables won't cause errors—they'll just be ignored in favor of the persisted settings.

## Canonical Operational Docs

- Full deployment steps: [../DEPLOYMENT.md](../DEPLOYMENT.md)
- Migration deltas: [../MIGRATION.md](../MIGRATION.md)
- Root quick start: [../README.md](../README.md)
