# Motion In Ocean - Container Deployment Patterns

> **Doc ownership**
>
> - **This file should contain:** container directory layout, compose overlay patterns, and repository-specific container composition conventions.
> - **This file should not contain:** generic startup, environment-variable walkthroughs, or full deployment runbooks duplicated from root docs.

## Purpose of `containers/`

This directory defines the **deployment packaging pattern** used by Motion In Ocean:

- One deployment per directory
- `docker-compose.yaml` entrypoint in each deployment
- Optional overlays for specialized behavior
- Clear separation between webcam and management roles

## Container Registry

Images are published to both registries when a GitHub Release is published:

| Registry                            | Image                                  |
| ----------------------------------- | -------------------------------------- |
| GitHub Container Registry (default) | `ghcr.io/cyanautomation/motioninocean` |
| Docker Hub                          | `cyanautomation/motioninocean`         |

The compose files default to GHCR. To use Docker Hub instead, override `MIO_IMAGE_TAG` and change the `image:` value in your local copy:

```yaml
image: cyanautomation/motioninocean:${MIO_IMAGE_TAG:-latest}
```

## Directory Pattern

```
containers/
├── motion-in-ocean-webcam/
│   ├── docker-compose.yaml
│   ├── docker-compose.hardened.yaml
│   ├── docker-compose.mock.yaml
│   └── .env.example
│
├── motion-in-ocean-management/
│   ├── docker-compose.yaml
│   └── .env.example
│
└── shared/
```

## Overlay Conventions

### Webcam Base

- `motion-in-ocean-webcam/docker-compose.yaml` is the base streaming deployment.

### Hardened Overlay

- `motion-in-ocean-webcam/docker-compose.hardened.yaml` is layered on top of webcam base for stricter device/security posture.
- Intended to be combined with host-specific device mapping workflows.

### Mock Overlay

- `motion-in-ocean-webcam/docker-compose.mock.yaml` is layered on top of webcam base for hardware-free validation/testing. It enables `MIO_MOCK_CAMERA` and removes camera device access.

### Management Base

- `motion-in-ocean-management/docker-compose.yaml` is the management/control-plane deployment.

## Composition Examples (Pattern-Only)

```bash
# Base webcam
(cd containers/motion-in-ocean-webcam && docker compose up -d)

# Webcam + hardened overlay
(cd containers/motion-in-ocean-webcam && docker compose -f docker-compose.yaml -f docker-compose.hardened.yaml up -d)

# Webcam + mock overlay
(cd containers/motion-in-ocean-webcam && docker compose -f docker-compose.yaml -f docker-compose.mock.yaml up -d)
```

The Compose files default to `linux/arm64` for Raspberry Pi. Set `MIO_COMPOSE_PLATFORM=linux/amd64` before the Compose command to use the native AMD64 image on an x86 development host.

## Canonical App Vars vs Docker/Compose Keys

- **Canonical app env vars:** `MIO_*` (for example: `MIO_APP_MODE`, `MIO_PORT`, `MIO_BIND_HOST`).
- **Standard Docker/Compose keys (not app env vars):** `image`, `ports`, `environment`, `volumes`, `networks`, `depends_on`, `restart`.

### Deprecated compatibility variables still accepted

| Deprecated variable                  | Preferred variable          |
| ------------------------------------ | --------------------------- |
| `MIO_PI3_PROFILE`                    | `MIO_PERFORMANCE_PROFILE`   |
| `MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS`  | `MIO_ALLOW_PRIVATE_IPS`     |

Other historical names such as `APP_MODE` and `RESOLUTION` are not read by the current runtime. See the [deployment guide](../docs/guides/DEPLOYMENT.md) for compatibility behavior and the [environment variable reference](../docs/ENVIRONMENT_VARIABLES_DOCUMENTATION_COMPLETE.md) for supported names.

## Configuration Model: Infrastructure vs. Runtime Settings

**Motion In Ocean separates configuration into two distinct categories:**

### Infrastructure Configuration (Environment Variables in docker-compose/.env)

These settings control deployment and system behavior, and are set at container startup. They **cannot** be modified via the web UI.

**Webcam mode:**

- `MIO_PORT`, `MIO_BIND_HOST` — Network binding
- `MIO_MOCK_CAMERA` — Mock camera for testing
- `MIO_PERFORMANCE_PROFILE` — hardware performance profile (`MIO_PI3_PROFILE` is deprecated)
- OctoPrint compatibility is always enabled in webcam mode; `MIO_OCTOPRINT_COMPATIBILITY` and `OCTOPRINT_COMPATIBILITY` are deprecated/ignored.
- `MIO_WEBCAM_CONTROL_PLANE_AUTH_TOKEN` — optional bearer token for webcam control-plane routes
- `MIO_APPLICATION_SETTINGS_PATH`, `MIO_NODE_REGISTRY_PATH` — Persistence locations
- `MIO_SENTRY_DSN` — Optional error tracking. The image must be built with
  `--build-arg INSTALL_SENTRY_SDK=true` for Sentry reporting to be enabled.
- `MIO_LIMITER_STORAGE_URI` — Rate-limit storage URI. The built-in `memory://`
  backend is the default; other backends require an image built with
  `--build-arg INSTALL_EXTERNAL_LIMITER=true`.

**Management mode:**

- Same network, persistence, and system settings as webcam
- Plus: `MIO_NODE_DISCOVERY_SHARED_SECRET`, `MIO_ALLOW_PRIVATE_IPS` — Discovery security
- Plus: `MIO_DOCKER_PROXY_PORT` — Docker transport support

See the webcam and management `.env.example` files for deployment defaults, and the [runtime environment variable reference](../docs/ENVIRONMENT_VARIABLES_DOCUMENTATION_COMPLETE.md) for application variables.

### Runtime Settings (Web UI, persisted to /data/application-settings.json)

These settings control camera behavior, logging, discovery, and feature flags. They can be managed through the web UI at runtime and changes **do not require a container restart**. Supported environment variables supply defaults when a persisted value is not set.

**Available categories:**

1. **Camera Settings** — Resolution, FPS, JPEG quality, stream connections, frame age
2. **Logging Settings** — Log level, format, identifier inclusion
3. **Discovery Settings** — Enable/disable, management URL, token, interval (`MIO_DISCOVERY_ENABLED`, `MIO_DISCOVERY_MANAGEMENT_URL`, `MIO_DISCOVERY_TOKEN`, `MIO_DISCOVERY_INTERVAL_SECONDS`)
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
# (Only deployment-level configuration; set MIO_BIND_HOST, MIO_PORT, etc.)
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

1. Remove them from your `.env` file if you want to manage those settings only through the UI
2. Start the container normally
3. Use the web UI to configure camera, logging, and feature flag settings
4. Persisted values in `/data/application-settings.json` take precedence; environment values remain defaults when a persisted value is unset.

The current runtime continues to support documented `MIO_*` environment settings. Names not listed in the runtime reference are not supported.

## Canonical Operational Docs

- Full deployment steps: [DEPLOYMENT.md](../docs/guides/DEPLOYMENT.md)
- Migration deltas: [MIGRATION.md](../docs/guides/MIGRATION.md)
- Root quick start: [../README.md](../README.md)
