# Security Policy

## Supported Versions

motion-in-ocean is currently in early development and focuses on Raspberry Pi OS / Debian Bookworm ARM64.

Security fixes are applied to:
- `main` branch
- the most recent tagged release (if releases exist)

---

## Reporting a Vulnerability

If you discover a security issue, please **do not open a public GitHub issue**.

Instead:

1. Use GitHub's **Private Vulnerability Reporting** (recommended), if enabled  
2. Or email the maintainer directly (if contact details are listed in the repo)

Please include:

- Description of the vulnerability
- Impact and risk level
- Steps to reproduce
- Any suggested fix / mitigation

---

## Threat model & security notes

motion-in-ocean is a homelab-oriented container and requires access to Raspberry Pi camera devices.

Important security considerations:

- The container may require access to sensitive host device nodes (e.g. `/dev/vchiq`, `/dev/video*`)
- The service may be accessible over LAN depending on compose configuration
- The HTTP service is not intended to be publicly exposed

### Management mode threat model

When `APP_MODE=management`, the service acts as a control plane and can mutate node definitions and invoke remote actions. In this mode, security boundaries are:

- **Management write API** (`POST/PUT/DELETE /api/nodes*`, `POST /api/nodes/<id>/actions/<action>`): must be treated as privileged and protected with API tokens.
- **Outbound node communication** (`base_url` probes and actions): can become SSRF/open-proxy behavior if unrestricted.
- **Docker transport operations**: should be considered highly privileged host-control operations and must remain explicitly disabled unless intentionally enabled.

Implemented hardening controls:

- Write endpoints support token-based auth with role separation (`write` and `admin`).
- Docker transport actions require `admin` role and explicit opt-in (`MANAGEMENT_DOCKER_SOCKET_ENABLED=true`).
- Outbound requests validate URL scheme/host and enforce optional hostname allowlist (`MANAGEMENT_OUTBOUND_ALLOWLIST`).
- Private/loopback/link-local/metadata hosts are blocked for management outbound requests.

### Recommended mitigations

- Bind to localhost where possible:
  ```yaml
  ports:
    - "127.0.0.1:8000:8000"
  ```

* If remote access is needed, use a reverse proxy with authentication (Caddy/Nginx/Traefik)
* Do not expose the service to the public internet without access controls

### Deployment hardening checklist (management mode)

- [ ] Set `MOTION_IN_OCEAN_APP_MODE=management` only for control-plane deployments.
- [ ] Enable management write auth with `MOTION_IN_OCEAN_MANAGEMENT_AUTH_REQUIRED=true`.
- [ ] Configure strong, rotated secrets for:
  - `MOTION_IN_OCEAN_MANAGEMENT_WRITE_API_TOKENS`
  - `MOTION_IN_OCEAN_MANAGEMENT_ADMIN_API_TOKENS`
- [ ] Set `MOTION_IN_OCEAN_MANAGEMENT_OUTBOUND_ALLOWLIST` to approved node hostnames.
- [ ] Keep `MOTION_IN_OCEAN_MANAGEMENT_DOCKER_SOCKET_ENABLED=false` unless docker transport is explicitly required.
- [ ] If docker transport is enabled, restrict admin tokens and isolate host socket access.
- [ ] Bind service to trusted networks only and front with authenticated reverse proxy when remote access is needed.
- [ ] Monitor management API logs for rejected auth and outbound policy violations.

---

## Dependency management

This project relies on:

* libcamera + Picamera2 stack
* OS-level packages from Raspberry Pi OS / Debian Bookworm
* Python packages from `requirements.txt`

Security updates should include:

* rebuilding images when base images or OS packages are updated
* keeping python dependencies current when feasible

---

## Disclosure policy

If a security issue is confirmed:

* a fix will be prepared privately when possible
* a patch will be released to `main`
* a release note may be published describing the issue at a high level

Thank you for helping keep motion-in-ocean secure.
