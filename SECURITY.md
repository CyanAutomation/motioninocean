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

Additional security and operational references:
- [Documentation index](docs/README.md)
- [Deployment guide](docs/guides/DEPLOYMENT.md)


motion-in-ocean is a homelab-oriented container and requires access to Raspberry Pi camera devices.

Important security considerations:

- The container may require access to sensitive host device nodes (e.g. `/dev/vchiq`, `/dev/video*`)
- The service may be accessible over LAN depending on compose configuration
- The HTTP service is not intended to be publicly exposed

### Recommended mitigations

- Bind to localhost where possible:
  ```yaml
  ports:
    - "127.0.0.1:8000:8000"
  ```

* If remote access is needed, use bearer token authentication (see docs/guides/DEPLOYMENT.md)
* Do not expose the service to the public internet without access controls

---

## Dependency management

This project relies on:

- libcamera + Picamera2 stack
- OS-level packages from Raspberry Pi OS / Debian Bookworm
- Python packages from `requirements.txt`

Security updates should include:

- rebuilding images when base images or OS packages are updated
- keeping python dependencies current when feasible

---

## Disclosure policy

If a security issue is confirmed:

- a fix will be prepared privately when possible
- a patch will be released to `main`
- a release note may be published describing the issue at a high level

Thank you for helping keep motion-in-ocean secure.
