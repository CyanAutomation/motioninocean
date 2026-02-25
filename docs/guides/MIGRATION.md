# Migration Guide: Version-to-Version Deltas

> **Doc ownership**
>
> - **This file should contain:** version deltas, breaking-change summaries, and what changed between releases.
> - **This file should not contain:** full setup/run commands that already live in `DEPLOYMENT.md`.

---

## v3: Directory-Based Deployment (Breaking Change)

**Status:** Released February 11, 2026 ✅

### Delta Summary

- Deployment moved from root-level custom compose filenames to directory-based deployments under `containers/`.
- Tooling compatibility improved by standardizing on `docker-compose.yml` inside each deployment directory.
- Legacy root-level compose files are deprecated and on a removal path.

### Old → New Pattern

| Area                | Old (Deprecated)                                  | New (Recommended)                                             |
| ------------------- | ------------------------------------------------- | ------------------------------------------------------------- |
| Compose location    | Project root (`docker-compose.webcam.yaml`, etc.) | `containers/motioniocean-{mode}/docker-compose.yml`           |
| Compose invocation  | `docker compose -f <file> ...`                    | `cd containers/motioniocean-{mode}` then `docker compose ...` |
| Configuration scope | Single root-oriented workflow                     | Per-deployment isolated `.env` + overlays                     |

### What You Need To Change

- Update automation/scripts that depend on `-f docker-compose.*.yaml` to run from deployment directories.
- Migrate operational runbooks to directory-based commands.
- Plan removal of legacy root-level compose usage in future releases.

For step-by-step migration execution, use the canonical sections in `DEPLOYMENT.md`:

- [Recommended: Directory-Based Deployment](DEPLOYMENT.md#recommended-directory-based-deployment)
- [Legacy: Root-Level Compose Files](DEPLOYMENT.md#legacy-root-level-compose-files)
- [Multi-Host Setup (Directory-Based)](DEPLOYMENT.md#multi-host-setup-directory-based)

---

## v2: Docker Configuration Simplification (Breaking Change)

**Status:** Released February 11, 2026 ✅

### Delta Summary

- Environment schema simplified from many toggles to a minimal default set.
- Authentication model changed from boolean+token to token-only semantics.
- Healthcheck behavior standardized.

### Compose & Runtime Behavior Delta

| Aspect                | Old                                        | New                                                  |
| --------------------- | ------------------------------------------ | ---------------------------------------------------- |
| Compose strategy      | Larger config surface with legacy patterns | Simplified defaults aligned to deployment modes      |
| Device access posture | Explicit mappings/cgroup rules emphasis    | Simpler default posture (with hardened overlay path) |
| Healthcheck           | Python-script based checks                 | HTTP endpoint checks                                 |

### Environment Variable Delta

#### Removed / Reworked Variables

| Old Variable                        | New Status                        |
| ----------------------------------- | --------------------------------- |
| `MANAGEMENT_AUTH_REQUIRED`          | Removed (token-only auth model)   |
| `MOTION_IN_OCEAN_HEALTHCHECK_READY` | Removed                           |
| `DOCKER_PROXY_PORT`                 | Removed                           |
| `MOTION_IN_OCEAN_BIND_HOST`         | Removed from standard env surface |

#### Still Supported (Advanced / Undocumented)

- `MOTION_IN_OCEAN_RESOLUTION`
- `MOTION_IN_OCEAN_FPS`
- `MOTION_IN_OCEAN_TARGET_FPS`
- `MOTION_IN_OCEAN_JPEG_QUALITY`
- `MOTION_IN_OCEAN_MAX_STREAM_CONNECTIONS`
- `MOTION_IN_OCEAN_PI3_PROFILE` (deprecated; map to `MIO_PERFORMANCE_PROFILE=pi3`)
- `MOTION_IN_OCEAN_CORS_ORIGINS`

#### Removed legacy aliases (must migrate to canonical `MIO_*`)

- `PI3_PROFILE` → `MIO_PI3_PROFILE` (deprecated compatibility alias)
- `MOCK_CAMERA` → `MIO_MOCK_CAMERA`
- `MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS` → `MIO_ALLOW_PRIVATE_IPS`


### OctoPrint Compatibility Model Change

In webcam mode, OctoPrint compatibility is always enabled.

- `MIO_OCTOPRINT_COMPATIBILITY` is removed from runtime handling and ignored silently.
- `OCTOPRINT_COMPATIBILITY` is removed from runtime handling and ignored silently.
- Setting either variable has no runtime effect and does not emit warnings.

### Authentication Delta

| Old Model                          | New Model                                               |
| ---------------------------------- | ------------------------------------------------------- | ---------------------------- |
| `MANAGEMENT_AUTH_REQUIRED=true     | false`+`MANAGEMENT_AUTH_TOKEN`                          | `MANAGEMENT_AUTH_TOKEN` only |
| Boolean gate controlled auth state | Empty token disables auth; non-empty token enables auth |

For canonical runtime/security setup details, use:

- [Security Considerations](DEPLOYMENT.md#security-considerations)
- [Scenario 2: Docker Socket Proxy (Advanced)](DEPLOYMENT.md#scenario-2-docker-socket-proxy-advanced)
- [Troubleshooting](DEPLOYMENT.md#troubleshooting)


### Performance profile migration (Pi 3 tuning)

Motion In Ocean now models hardware tuning as an explicit preset:

- `MIO_PERFORMANCE_PROFILE=default|pi3` (**new canonical setting**)
- `MIO_PI3_PROFILE=true|false` (**deprecated compatibility alias**)

Behavior and precedence:

1. Explicit camera env vars such as `MIO_FPS`, `MIO_RESOLUTION`, and `MIO_JPEG_QUALITY` always win.
2. `MIO_PERFORMANCE_PROFILE` supplies baseline defaults when those explicit vars are unset.
3. If `MIO_PERFORMANCE_PROFILE` is unset and `MIO_PI3_PROFILE=true`, runtime maps to `pi3` and logs a deprecation warning.

Removal timeline:

- **v3.x:** `MIO_PI3_PROFILE` supported with deprecation warning.
- **v4.0 (planned):** `MIO_PI3_PROFILE` removed; use `MIO_PERFORMANCE_PROFILE=pi3`.
