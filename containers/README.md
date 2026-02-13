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

## Canonical Operational Docs

- Full deployment steps: [../DEPLOYMENT.md](../DEPLOYMENT.md)
- Migration deltas: [../MIGRATION.md](../MIGRATION.md)
- Root quick start: [../README.md](../README.md)
