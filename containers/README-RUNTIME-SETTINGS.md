# Runtime Configuration Management

## Overview

Motion In Ocean supports **runtime configuration management** through the web UI 🎛️, allowing you to modify many settings without restarting containers or editing environment files.

## Canonical App Vars vs Docker/Compose Keys

- **Canonical app env vars:** `MIO_*` names for application behavior.
- **Docker/Compose keys:** `image`, `ports`, `environment`, `volumes`, `networks`, and related compose schema keys are not env vars.

### Legacy aliases still accepted temporarily

| Canonical `MIO_*` var       | Legacy alias                               |
| --------------------------- | ------------------------------------------ |
| `MIO_APP_MODE`              | `APP_MODE`, `MOTION_IN_OCEAN_MODE`         |
| `MIO_PORT`                  | `MOTION_IN_OCEAN_PORT`                     |
| `MIO_BIND_HOST`             | `MOTION_IN_OCEAN_BIND_HOST`                |
| `MIO_RESOLUTION`            | `RESOLUTION`, `MOTION_IN_OCEAN_RESOLUTION` |
| `MIO_MANAGEMENT_AUTH_TOKEN` | `MANAGEMENT_AUTH_TOKEN`                    |
| `MIO_DISCOVERY_TOKEN`       | `DISCOVERY_TOKEN`                          |

## How It Works

1. **Environment Variables as System Defaults**
   - Values in `.env` files serve as system defaults
   - Environment variables are read at container startup
   - These defaults persist if no UI changes are made

2. **UI Settings Override Environment Variables**
   - Changes made via the web UI Settings panel override environment defaults
   - Settings are persisted to `APPLICATION_SETTINGS_PATH` (default: `/data/application-settings.json`)
   - Persisted settings survive container restarts
   - Environment variables always act as fallback when no persisted value exists

3. **Change Propagation**
   - **Immediate**: Most settings (logging, discovery, camera) take effect immediately
   - **Restart Required**: Some settings (marked in UI) require container restart to apply

## Settings Categories

### Camera Configuration (Immediate)

Settings that affect video capture and streaming:

- `MIO_RESOLUTION` - Video resolution
- `MIO_FPS` - Frames per second
- `MIO_JPEG_QUALITY` - Compression quality (1-100)
- `MIO_MAX_STREAM_CONNECTIONS` - Concurrent connections limit
- `MAX_FRAME_AGE_SECONDS` - Frame cache duration

**UI Location**: Settings tab → Camera Configuration

### Logging Configuration (Immediate)

Settings that control logging behavior:

- `LOG_LEVEL` - Verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_FORMAT` - Output format (text or json)
- `LOG_INCLUDE_IDENTIFIERS` - Include process/thread IDs

**UI Location**: Settings tab → Logging Configuration

### Node Discovery (Immediate)

Settings for registering with a management node:

- `DISCOVERY_ENABLED` - Enable/disable discovery
- `DISCOVERY_MANAGEMENT_URL` - Management node URL
- `MIO_DISCOVERY_TOKEN` - Authentication token
- `DISCOVERY_INTERVAL_SECONDS` - Announcement frequency

**UI Location**: Settings tab → Node Discovery

### Feature Flags (Varies)

Experimental features that can be toggled:

- `MIO_QUALITY_ADAPTATION` - Auto JPEG quality adjustment
- `MIO_FPS_THROTTLE_ADAPTIVE` - Adaptive frame rate
- `MIO_FRAME_SIZE_OPTIMIZATION` - Client-aware resolution
- `MIO_PI3_OPTIMIZATION` - Raspberry Pi 3 optimizations
- `MIO_PI5_OPTIMIZATION` - Raspberry Pi 5 optimizations
- And more...

**UI Location**: Settings tab → Feature Flags

## Which Settings are NOT Runtime-Editable?

These environment variables are **system configuration** and require container restart to change:

### Deployment & Infrastructure

- `MIO_IMAGE_TAG` - Docker image version
- `MIO_PORT` - Web server port
- `MIO_BIND_HOST` - Network bind address
- `TZ` - Timezone
- `BASE_URL` - Public URL (if using discovery with remote management)

### Security & Authentication

- `MIO_MANAGEMENT_AUTH_TOKEN` - API authentication token (management mode)
- `NODE_DISCOVERY_SHARED_SECRET` - Discovery authentication (management mode)

### Hardware & Mode Configuration

- `MIO_APP_MODE` - Application mode (webcam or management)
- `MOCK_CAMERA` - Enable synthetic camera
- `MIO_OCTOPRINT_COMPATIBILITY` - **Deprecated/ignored** (OctoPrint compatibility is built in; remove this variable)
- `MIO_PI3_PROFILE` - Raspberry Pi 3 mode

### Advanced Configuration

- `NODE_REGISTRY_PATH` - Store path for node registry
- `APPLICATION_SETTINGS_PATH` - Store path for runtime settings JSON/lock files
- `LIMITER_STORAGE_URI` - Rate limiter backend
- `DOCKER_PROXY_PORT` - Docker connectivity settings

## Accessing Runtime Settings

### Via Web UI

1. Open the motion-in-ocean web interface
2. Click the **🎛️ Settings** tab
3. Modify values in the appropriate category
4. Click **Save** to persist changes

### Via API

**Get all settings:**

```bash
curl http://localhost:8000/api/settings
```

**Update settings:**

```bash
curl -X PATCH http://localhost:8000/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "camera": {
      "fps": 60,
      "jpeg_quality": 80
    },
    "logging": {
      "log_level": "DEBUG"
    }
  }'
```

**Get schema:**

```bash
curl http://localhost:8000/api/settings/schema
```

**Reset to defaults:**

```bash
curl -X POST http://localhost:8000/api/settings/reset
```

**View what's been overridden:**

```bash
curl http://localhost:8000/api/settings/changes
```

## Persistence & Recovery

### Settings Storage

- Runtime settings are stored in `APPLICATION_SETTINGS_PATH` (default: `/data/application-settings.json`)
- This file must be mounted as a volume for persistence across restarts
- File has atomic writes and file locking for safe concurrent access

### Default Recovery

To restore all settings to environment-variable defaults:

1. Via UI: Settings tab → **Reset to Defaults** button
2. Via API: `POST /api/settings/reset`
3. Via filesystem: Delete the file pointed to by `APPLICATION_SETTINGS_PATH` and restart the container

### Volume Configuration

Ensure your docker-compose or container configuration includes:

```yaml
volumes:
  - data:/data # Persists application-settings.json
```

### Restricted Deployments (Read-Only /data)

If `/data` is read-only in your environment, set a writable alternate path:

```yaml
services:
  motion-in-ocean:
    environment:
      APPLICATION_SETTINGS_PATH: /tmp/motion-in-ocean/application-settings.json
    tmpfs:
      - /tmp
```

This keeps runtime settings and lock files writable even when `/data` cannot be written.

### Ownership & Permissions at Startup

- The container entrypoint checks whether `/data` is writable during startup and logs the effective UID used for that check.
- When the container starts as `root` (default image behavior), it attempts `chown -R 10001:10001 /data` before launching the Python app as the `app` user (`uid=10001`).
- If you override the container to run as non-root only (for example, `user: "10001:10001"`), pre-create and chown the host volume path first:

```bash
mkdir -p ./motion-in-ocean-data
sudo chown -R 10001:10001 ./motion-in-ocean-data
```

## Reference: .env Annotations

Look for `[UI MANAGEABLE]` comments in `.env.example` files to identify which settings can be changed via the UI without restarting.

Example:

```dotenv
# Camera FPS (Frames Per Second)
# Default: 30
# [UI MANAGEABLE] Runtime-editable via Settings tab
MIO_FPS=30
```

## Best Practices

1. **Use Environment Variables for Infrastructure**
   - Set `MIO_PORT`, `MIO_BIND_HOST` in `.env`
   - These rarely need to change

2. **Use UI Settings for Tuning**
   - Adjust `FPS`, `JPEG_QUALITY`, `LOG_LEVEL` via UI
   - No restart needed; changes take effect immediately

3. **Document Your Overrides**
   - Note important settings overrides on a wiki or deployment doc
   - Check `/api/settings/changes` to see current overrides

4. **Monitor During Tuning**
   - After changing performance settings (`FPS`, quality, connections)
   - Watch system resources and logs for impact
   - Revert if performance degrades

## Troubleshooting

### Settings don't persist

- Check that `/data/` volume is writable
- Check file permissions on the path configured by `APPLICATION_SETTINGS_PATH`
- View logs for validation errors

### Settings revert after restart

- The `/data` volume may not be properly mounted
- Verify volume configuration in docker-compose
- Check that volume path exists on host

### UI shows different values than environment

- This is expected! UI overrides take precedence
- Use `/api/settings/changes` to see what's been overridden
- Use `/api/settings/reset` to return to environment defaults

---

**Last Updated**: 2026-02-15  
**Version**: Motion In Ocean v1.0+
