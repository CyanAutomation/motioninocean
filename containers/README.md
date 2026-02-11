# Motion In Ocean - Container Deployment Patterns

This directory contains standardized directory-based deployment configurations for Motion In Ocean. This structure ensures **tool compatibility** (e.g., Dockhand) and provides clear **isolation** between deployments.

## Directory Structure

```
containers/
├── motioniocean-webcam/
│   ├── docker-compose.yml          # Main streaming configuration
│   ├── docker-compose.hardened.yml # Production security overlay
│   ├── docker-compose.mock.yml     # Mock camera testing overlay
│   └── .env.example                # Configuration template
│
├── motioniocean-management/
│   ├── docker-compose.yml          # Node registry hub
│   └── .env.example                # Configuration template
│
└── shared/                         # Shared resources
    └── (future: shared volumes, certs, etc.)
```

## Quick Start

### Webcam Mode (Camera Streaming)

```bash
cd containers/motioniocean-webcam
cp .env.example .env
# Edit .env if needed (port, resolution, etc.)
docker compose up -d
```

Access at: `http://localhost:8000`

### Management Mode (Node Coordination Hub)

```bash
cd containers/motioniocean-management
cp .env.example .env
# Edit .env if needed (port, etc.)
docker compose up -d
```

Access at: `http://localhost:8001`

## Advanced Usage

### Hardened Security (Production)

Use explicit device mappings instead of privileged mode:

```bash
cd containers/motioniocean-webcam
docker compose -f docker-compose.yml -f docker-compose.hardened.yml up -d
```

This requires your host to have the correct device nodes (run `../../detect-devices.sh` from bash).

### Mock Camera (Testing without Hardware)

Test without camera hardware:

```bash
cd containers/motioniocean-webcam
docker compose -f docker-compose.yml -f docker-compose.mock.yml up -d
```

### Auto-Detect Device Mappings

For hardened mode, auto-generate device mappings on your host:

```bash
cd containers/motioniocean-webcam
../../detect-devices.sh
# Generates docker-compose.override.yml with host-specific devices
docker compose -f docker-compose.yml -f docker-compose.hardened.yml up -d
```

## Deployment on Another Host

To deploy to a remote machine (e.g., Raspberry Pi):

1. Copy this entire `containers/motioniocean-{mode}/` directory to the target machine
2. Copy the mode you need (webcam or management) to `~/containers/motioniocean-{mode}/`
3. Edit `.env` with target-specific settings
4. Run `docker compose up -d`

Example:

```bash
# On your workstation
scp -r containers/motioniocean-webcam pi@192.168.1.100:~/containers/motioniocean-webcam

# On the Pi
ssh pi@192.168.1.100
cd ~/containers/motioniocean-webcam
cp .env.example .env
nano .env  # Review settings
docker compose up -d
```

## Port Assignment

- **Webcam mode:** Port 8000 (default)
- **Management mode:** Port 8001 (default)

Configure in `.env`: `MOTION_IN_OCEAN_PORT=8000`

## Environment Variables

Each directory includes `.env.example`. Common variables:

- `MOTION_IN_OCEAN_IMAGE_TAG`: Docker image version (default: latest)
- `MOTION_IN_OCEAN_PORT`: HTTP port (default: 8000 or 8001)
- `MOTION_IN_OCEAN_BIND_HOST`: Bind address (default: 127.0.0.1)
- `TZ`: Timezone (default: Europe/London)
- `MANAGEMENT_AUTH_TOKEN`: Optional auth token (leave empty to disable)

## Overlays & Composition

Standard Docker Compose overlays allow flexible composition:

```bash
# Webcam + Hardened + Mock (test with security hardening)
docker compose \
  -f docker-compose.yml \
  -f docker-compose.hardened.yml \
  -f docker-compose.mock.yml \
  up -d
```

## Multi-Host Setup (Webcam Nodes + Management Hub)

For a distributed setup:

1. **Management Hub** (on a stable host):

   ```bash
   cd containers/motioniocean-management
   docker compose up -d
   ```

2. **Webcam Nodes** (on cameras, e.g., Pis):
   ```bash
   cd containers/motioniocean-webcam
   docker compose up -d
   ```

Set `MANAGEMENT_AUTH_TOKEN` in both `.env` files to the same value for secure communication.

## Troubleshooting

### Ports Already in Use

Modify `.env`:

```bash
MOTION_IN_OCEAN_PORT=8080  # Use 8080 instead of 8000
```

### Camera Not Working

1. Run device detection (if using webcam mode):

   ```bash
   ../../detect-devices.sh
   ```

2. Check logs:

   ```bash
   docker compose logs -f motion-in-ocean
   ```

3. Try mock mode to isolate hardware issues:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.mock.yml up -d
   ```

### Test Connectivity (Health Check)

```bash
curl http://localhost:8000/health
```

## Deprecated: Root-Level Compose Files

The repository previously included multiple custom-named compose files in the root directory:

- `docker-compose.webcam.yaml`
- `docker-compose.management.yaml`
- `docker-compose.hardened.yaml`
- `docker-compose.mock.yaml`

These are **deprecated in favor of directory-based deployments** (this directory). See [MIGRATION.md](../MIGRATION.md) for migration guidance.

## Contributing

When testing locally:

1. Use the appropriate container directory
2. Copy `.env.example` and customize
3. Test with standard `docker compose up -d` (no `-f` flags needed)
4. Report issues with the specific deployment path (e.g., "webcam mode, hardened overlay")

---

**For more information:** See [DEPLOYMENT.md](../DEPLOYMENT.md) and [README.md](../README.md) in the root directory.
