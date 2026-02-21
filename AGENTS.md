# AGENTS.md

**Motion In Ocean** is a Docker-first Raspberry Pi CSI camera streaming solution with multi-node management.

This file provides guidance for AI coding agents working on motion-in-ocean. For human contributors, see [CONTRIBUTING.md](CONTRIBUTING.md) and [README.md](README.md).

---

## Project Overview

Motion In Ocean enables reliable, stateless camera streaming for Raspberry Pi in containerized environments (Docker/Docker Compose). It supports:

- **Webcam Mode** (port 8000): Streams camera output via MJPEG, exposes REST API for settings and actions
- **Management Mode** (port 8001): Hub that discovers and manages remote webcam nodes, aggregates status, manages node registry
- **Auto-Discovery**: Webcam nodes self-register with management hub via bearer-token-authenticated announcements
- **Multi-Host**: Hub-and-spoke architecture for distributed deployments across multiple Raspberry Pi platforms

**Domain**: IoT/Edge Computing, camera streaming, homelab integration (Home Assistant, OctoPrint, etc.)

**Tech Stack**:

- Python 3.9+ (3.11+ recommended)
- Flask (lightweight HTTP API)
- Picamera2 / libcamera (modern RPi camera support)
- Docker / Docker Compose (all deployments containerized)
- JavaScript/HTML/CSS (web UI for streaming viewer and management dashboard)

---

## Architecture

### Two Deployable Modes

**Webcam Mode** processes camera frames and streams video:

```
[Picamera2 Hardware] → [FrameBuffer] → [MJPEG Encoder] → [HTTP /stream endpoint]
                            ↓
                      [StreamStats]
                            ↓
                      [REST API: /api/status, /api/settings]
```

Files: [pi_camera_in_docker/modes/webcam.py](pi_camera_in_docker/modes/webcam.py)

**Management Mode** aggregates remote nodes:

```
[Browser/Client] → [Management Hub] → [Node Registry] → [HTTP to /api/status on remote nodes]
                        ↓
                  [DiscoveryAnnouncer listener]
                  (receives self-registration from webcam nodes)
```

Files: [pi_camera_in_docker/management_api.py](pi_camera_in_docker/management_api.py), [pi_camera_in_docker/discovery.py](pi_camera_in_docker/discovery.py)

### Configuration Precedence

1. Environment variables (set at container startup) — **highest priority**
2. Persisted JSON settings (`/data/application-settings.json`) — runtime overrides
3. Schema defaults — fallback values

See [pi_camera_in_docker/runtime_config.py](pi_camera_in_docker/runtime_config.py) and [pi_camera_in_docker/application_settings.py](pi_camera_in_docker/application_settings.py).

### Key Modules

| Module                          | Purpose                                                 |
| ------------------------------- | ------------------------------------------------------- |
| **main.py**                     | Flask app, mode detection, initialization               |
| **modes/webcam.py**             | Camera capture, frame buffer, MJPEG streaming           |
| **management_api.py**           | Node registry, discovery endpoints, SSRF validation     |
| **discovery.py**                | DiscoveryAnnouncer daemon thread (self-registration)    |
| **settings_api.py**             | `/api/settings` GET/PATCH endpoints, schema             |
| **shared.py**                   | Common routes: `/health`, `/ready`, `/metrics`          |
| **application_settings.py**     | Atomic file-based settings persistence                  |
| **runtime_config.py**           | Environment-based config loading, merging               |
| **feature_flags.py**            | Registry of feature gates (mock camera, adapters, etc.) |
| **config_validator.py**         | Runtime config validation with helpful error hints      |
| **settings_schema.py**          | JSON schema for all editable settings                   |
| **transport_url_validation.py** | SSRF protection, URL safeguarding                       |
| **cat_gif_generator.py**        | Fallback animated test GIF                              |
| **logging_config.py**           | Structured JSON logging setup                           |

Files: [pi_camera_in_docker/](pi_camera_in_ocean/)

---

## Dev Environment Setup

### Prerequisites

- Python 3.9+ (3.11+ recommended)
- Docker + Docker Compose
- Node.js 18+ (for UI testing only)
- Git

### Initial Setup

```bash
# Clone
git clone https://github.com/CyanAutomation/motioninocean.git
cd motioninocean

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dev dependencies
pip install -r requirements-dev.txt

# Install Node.js dependencies (for UI/Playwright testing)
npm install

# Setup pre-commit hooks
make pre-commit
```

### View All Available Commands

```bash
make help
```

---

## Build & Run Commands

### Local Development (Mock Camera)

Run the Flask app locally with mock camera (no hardware required):

```bash
# Terminal 1: Start Flask app in webcam mode with mock camera
make run-mock
# Opens at http://localhost:8000

# Terminal 2: Run tests
make test

# Terminal 3: Check code quality
make lint
make format
make type-check
make security
```

### Docker Build

```bash
# Build image with mock camera (testing)
make docker-build

# Build production image (real camera hardware only)
make docker-build-prod

# Build all variants
make docker-build-all

# Run container
make docker-run
```

### Docker Compose Deployments

See [containers/README.md](containers/README.md) for directory-based deployments (recommended).

**Quick start (webcam mode with mock camera, testing only):**

```bash
cd containers/motion-in-ocean-webcam
docker compose -f docker-compose.yml -f docker-compose.mock.yml up -d
```

**Quick start (webcam mode, real camera):**

```bash
cd containers/motion-in-ocean-webcam
docker compose up -d
```

**Quick start (management mode, hub):**

```bash
cd containers/motion-in-ocean-management
docker compose up -d
```

---

## Code Quality and Style

### Linting & Formatting

**Linter**: [Ruff](https://docs.astral.sh/ruff/) (Python code analysis)

```bash
# Check for lint violations
make lint

# Auto-fix violations
make lint-fix
```

**Formatter**: Ruff format (automatic code formatting)

```bash
# Auto-format all source code
make format
```

### Type Checking

**Tool**: [mypy](http://mypy-lang.org/) (static type analysis)

```bash
# Run type checker
make type-check
```

Expected: All files in `pi_camera_in_docker/` and `tests/` pass strict type checking.

### Security Checks

**Tool**: [Bandit](https://bandit.readthedocs.io/) (security-focused linter)

```bash
# Run security scanner
make security
```

Expected: No critical vulnerabilities. Warnings require review.

### Code Style Guidelines

- **Imports**: Organized groups (stdlib → third-party → local), sorted alphabetically within groups
- **Type hints**: Required for all public functions, class methods, and module-level variables
- **Line length**: Max 100 characters (enforced by Ruff)
- **Quote style**: Double quotes for strings (enforced by Ruff)
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes, `UPPERCASE` for constants

#### Documentation Requirements

**Python (Google-Style Docstrings)**

All public functions, classes, and methods must have Google-style docstrings with:

- Brief one-line description
- Detailed description (if needed)
- Args section: Parameter names, types, descriptions
- Returns section: Type and description
- Raises section: Exception types that can be raised
- Examples or Notes for complex logic

```python
"""Module for camera frame capture and streaming."""

from typing import Optional

from pi_camera_in_docker.shared import register_routes


def capture_frame(timeout_ms: Optional[int] = None) -> bytes:
    """Capture a single frame from camera.

    Acquires a frame from the camera hardware via picamera2 and encodes
    to JPEG format at the configured quality setting.

    Args:
        timeout_ms: Maximum wait time in milliseconds. If None, uses default
            from application settings. Must be greater than 0.

    Returns:
        JPEG-encoded frame bytes ready for streaming.

    Raises:
        RuntimeError: If camera is not initialized or frame capture fails.
        TimeoutError: If frame not ready within timeout_ms.
    """
    # Implementation
```

**JavaScript (JSDoc Comments)**

All public functions in JavaScript must have JSDoc headers with:

- Brief description tag @description or inline
- Parameter documentation @param with type and description
- Return type @returns with Promise<T> for async functions
- Exception information @throws for error cases
- @async for async functions

```javascript
/**
 * Fetch stream metadata from remote node.
 *
 * Queries /api/status endpoint with bearer token authentication.
 * Includes automatic retry with exponential backoff on network errors.
 *
 * @param {string} nodeId - Unique node identifier
 * @param {string} baseUrl - Node base URL (http[s]://host:port)
 * @param {string} authToken - Bearer token for authentication
 * @returns {Promise<Object>} Node status object with stream info
 * @throws {Error} If node unreachable after retries or auth fails
 * @async
 */
async function fetchNodeStatus(nodeId, baseUrl, authToken) {
  // Implementation
}
```

---

## Testing Instructions

### Test Suite Overview

- **Unit tests**: Fast, isolated, mock dependencies
- **Integration tests**: Real Flask app, mock camera, e2e flows
- **UI tests**: Playwright-based browser automation (streaming viewer, management dashboard)

### Run Tests

```bash
# Run all tests with coverage report
make test

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Generate HTML coverage report
make coverage
```

Coverage reports at: [htmlcov/index.html](htmlcov/index.html)

### Test Structure

```
tests/
├── unit/                          # Unit tests (mocked dependencies)
│   ├── test_application_settings.py
│   ├── test_config_validator.py
│   ├── test_feature_flags.py
│   └── ...
├── integration/                   # Integration tests (real Flask app, mock camera)
│   ├── test_webcam_api.py
│   ├── test_management_api.py
│   ├── test_discovery.py
│   └── ...
├── ui/                            # UI tests (Playwright browser automation)
│   ├── test_streaming_viewer.py
│   ├── test_management_dashboard.py
│   └── ...
└── conftest.py                    # Shared fixtures
```

### Writing Tests

**Pattern 1: Unit test with fixture**

```python
def test_feature_flag_default_value():
    """Feature flag returns default when not set."""
    flags = get_feature_flags(env_overrides={})
    assert flags.is_enabled("mock_camera") is False
```

**Pattern 2: Integration test with mock Flask app**

```python
def test_health_endpoint(app_client):
    """GET /health returns 200 with status=ok."""
    response = app_client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"
```

**Pattern 3: Setting-persistence test**

```python
def test_settings_patch_persisted(tmp_path, app_client):
    """PATCH /api/settings persists to JSON file."""
    # Patch setting
    response = app_client.patch(
        "/api/settings",
        json={"camera": {"resolution": "1280x720"}},
    )
    assert response.status_code == 200
    # Verify persistence
    settings = ApplicationSettings(settings_file=tmp_path / "settings.json")
    assert settings.camera_resolution == "1280x720"
```

### Mock Camera (No Hardware)

The `mock_camera` feature flag provides a fallback implementation when hardware is unavailable:

```python
if feature_flags.is_enabled("mock_camera"):
    from pi_camera_in_docker.cat_gif_generator import generate_cat_gif_frame
    frame = generate_cat_gif_frame()  # Animated cat GIF placeholder
else:
    frame = camera.capture_jpeg()  # Real Picamera2 hardware
```

Enable in tests or dev:

```bash
# Run with mock camera
export MOCK_CAMERA=true
make run-mock

# Or in docker-compose
docker compose -f docker-compose.yml -f docker-compose.mock.yml up -d
```

### Pre-Commit Checks

Before commit, verify:

```bash
# Run full CI suite locally (same as CI)
make ci

# Or individually:
make lint
make type-check
make security
make test
```

These checks are also enforced by GitHub Actions CI pipeline.

---

## REST API Patterns

### Authentication

Two bearer token mechanisms:

1. **Webcam token** (`WEBCAM_CONTROL_PLANE_AUTH_TOKEN` env var)
   - Protects: `/api/status`, `/health`, `/ready`, `/metrics`, `/api/actions/*` in webcam mode
   - Used by: Management hub when probing remote nodes

2. **Management token** (`MANAGEMENT_AUTH_TOKEN` env var)
   - Protects: `/api/nodes/*`, `/api/discovery/*` in management mode
   - Used by: Browser operator, node self-registration

Example request:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/status
```

### Common Endpoints

**Universal (both modes):**

```
GET  /health              → {"status": "ok"}
GET  /ready               → {"status": "ready"} / {"status": "waiting"}
GET  /metrics             → Prometheus-style metrics
```

**Webcam mode:**

```
GET  /stream              → MJPEG video stream
GET  /api/status          → {"status": "ok"|"degraded", "stream_available": bool, ...}
GET  /api/settings/schema → JSON schema describing all settings
PATCH /api/settings       → Update settings (persisted to JSON)
POST /api/settings/reset  → Revert to environment defaults
POST /api/actions/{action}→ Execute control-plane action
```

**Management mode:**

```
POST /api/discovery/announce       → Receive node self-registration
GET  /api/nodes                    → List all registered nodes
POST /api/nodes                    → Create new node
GET  /api/nodes/{id}               → Get node details
PATCH /api/nodes/{id}              → Update node
DELETE /api/nodes/{id}             → Remove node
POST /api/nodes/{id}/actions/{action} → Proxy action to remote node
```

### Response Format

All responses use JSON with consistent structure:

**Success (2xx):**

```json
{
  "status": "ok",
  "data": {
    /* response-specific data */
  }
}
```

**Error (4xx/5xx):**

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error description"
}
```

---

## Settings & Configuration

### Settings Schema

New settings must be defined in [pi_camera_in_docker/settings_schema.py](pi_camera_in_docker/settings_schema.py):

```python
SETTINGS_SCHEMA = {
    "camera": {
        "type": "object",
        "properties": {
            "resolution": {"type": "string", "default": "640x480"},
            "fps": {"type": "integer", "default": 24, "minimum": 1, "maximum": 120},
        },
    },
}
```

Then reference in [pi_camera_in_docker/runtime_config.py](pi_camera_in_docker/runtime_config.py) for precedence handling.

### Environment Variables

Key environment variables:

**Camera:**

- `RESOLUTION` (default: 640x480)
- `FPS` (default: 24)
- `JPEG_QUALITY` (1-100, default: 90)
- `MAX_STREAM_CONNECTIONS` (default: 5)

**Discovery:**

- `DISCOVERY_ENABLED` (default: false)
- `DISCOVERY_MANAGEMENT_URL` (example: <http://management-hub:8001>)
- `DISCOVERY_TOKEN` (must match `NODE_DISCOVERY_SHARED_SECRET` on management)
- `DISCOVERY_INTERVAL_SECONDS` (default: 60)

**Security:**

- `WEBCAM_CONTROL_PLANE_AUTH_TOKEN` (bearer token for webcam APIs)
- `MANAGEMENT_AUTH_TOKEN` (bearer token for management hub)
- `MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS` (enable SSRF bypass for private ranges, default: false)

**Advanced:**

- `APP_MODE` (webcam|management, default: webcam)
- `MOTION_IN_OCEAN_BIND_HOST` (default: 127.0.0.1, set to 0.0.0.0 for network access)
- `PI3_PROFILE` (true for RPi 3 resource optimization)
- `MOCK_CAMERA` (true to use animated GIF placeholder instead of hardware)
- `API_TEST_MODE_ENABLED` (true for deterministic testing)

---

## Security Considerations

### SSRF Protection

Management mode validates all outbound node URLs before proxying requests:

```python
# File: pi_camera_in_docker/transport_url_validation.py
def validate_url_for_management_mode(url: str) -> bool:
    """Reject localhost, private IPs, link-local, metadata endpoints."""
    # Blocks:
    # - 127.0.0.1, ::1 (localhost)
    # - 192.168.x.x, 10.x.x.x, 172.16-31.x.x (RFC1918)
    # - 169.254.x.x (link-local)
    # - 169.254.169.254 (AWS metadata)
    # etc.
    #
    # Override: Set MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS=true (internal networks only!)
```

**When adding node URL handling**, always:

1. Validate URLs through `validate_url_for_management_mode()`
2. Document why if bypassing SSRF checks
3. Ensure private IP allowance is opt-in via env var

### Authentication Boundaries

See [docs/guides/DEPLOYMENT.md#authentication-boundaries-and-headers](docs/guides/DEPLOYMENT.md#authentication-boundaries-and-headers) for detailed token flows.

**Three token paths:**

| Path                            | Token                             | Used For                          |
| ------------------------------- | --------------------------------- | --------------------------------- |
| Browser → Management            | `MANAGEMENT_AUTH_TOKEN`           | Protecting `/api/nodes/*`         |
| Webcam → Management (discovery) | `DISCOVERY_TOKEN`                 | Validating node self-registration |
| Management → Webcam             | `WEBCAM_CONTROL_PLANE_AUTH_TOKEN` | Probing remote `/api/status`      |

### Bearer Token Generation

```bash
# Generate strong random token (example)
openssl rand -hex 32
# Output: a3f8b9c2d7e1f4a6b8c9d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f
```

---

## UI Development & Testing

### Web UI

Frontend assets in [pi_camera_in_docker/static](pi_camera_in_docker/static) and [pi_camera_in_docker/templates](pi_camera_in_docker/templates):

```
ui/
├── templates/
│   ├── index.html         # Streaming viewer
│   └── management.html    # Node management dashboard
├── static/
│   ├── js/
│   │   ├── app.js         # Streaming viewer logic
│   │   ├── management.js  # Node management logic
│   │   └── settings.js    # Settings panel
│   └── css/
│       ├── style.css, theme.css, base.css
│       ├── components.css, management.css, settings.css
│       └── tabs-config.css
```

### Playwright UI Tests

Run full UI audit:

```bash
make audit-ui                  # All modes, all viewports
make audit-ui-webcam           # Webcam mode only
make audit-ui-management       # Management mode only
make audit-ui-interactive      # Inspector (manual testing)
```

Test patterns in [tests/ui/](tests/ui/):

```python
async def test_streaming_viewer_loads(page):
    """Streaming viewer loads and displays stream."""
    await page.goto("http://localhost:8000")
    assert await page.is_visible("video")
    # Verify stream connection attempt
    requests = await page.context.request.get("http://localhost:8000/stream")
```

---

## Common Agent Workflows

### Adding a New Setting

1. **Define in schema** ([pi_camera_in_docker/settings_schema.py](pi_camera_in_docker/settings_schema.py)):

   ```python
   SETTINGS_SCHEMA = {
       "camera": {
           "properties": {
               "new_setting": {"type": "string", "default": "value"},
           }
       }
   }
   ```

2. **Handle in runtime config** ([pi_camera_in_docker/runtime_config.py](pi_camera_in_docker/runtime_config.py)):

   ```python
   def load_config() -> dict:
       new_setting = env_or_persisted("NEW_SETTING", schema_default="value")
       return {"camera": {"new_setting": new_setting}}
   ```

3. **Use in application** ([pi_camera_in_docker/modes/webcam.py](pi_camera_in_docker/modes/webcam.py)):

   ```python
   setting_value = app.application_settings.new_setting
   ```

4. **Write test** (tests/integration/test_settings.py):

   ```python
   def test_new_setting_persists(app_client):
       response = app_client.patch("/api/settings", json={"camera": {"new_setting": "new_value"}})
       assert response.status_code == 200
   ```

### Testing a Mode Locally

**Webcam mode (with mock camera, no hardware):**

```bash
export MOCK_CAMERA=true
export APP_MODE=webcam
export MOTION_IN_OCEAN_BIND_HOST=0.0.0.0
make run-mock
# Access at http://localhost:8000
```

**Management mode (with mock webcam discovery):**

```bash
export APP_MODE=management
export MOTION_IN_OCEAN_BIND_HOST=0.0.0.0
make run-mock
# Access at http://localhost:8001
```

### Reproducing a Bug with Logs

Enable structured logging and capture output:

```bash
export MOTION_IN_OCEAN_LOG_LEVEL=DEBUG
export MOTION_IN_OCEAN_LOG_FORMAT=json
make run-mock 2>&1 | tee debug.log
```

Logs are JSON-formatted for easy parsing by tools.

### Running CI Locally

Reproduce all CI checks before push:

```bash
make ci  # Runs: lint, type-check, security, test
```

This is equivalent to the GitHub Actions pipeline.

---

## Deployment & Release

### Tag-Driven Release

Motion In Ocean uses semantic versioning with tag-triggered Docker publishing:

```bash
# Create a release tag (format: vX.Y.Z)
git tag v1.2.3
git push origin v1.2.3

# Tag-triggered workflow .github/workflows/docker-publish.yml:
# - Builds Docker image
# - Pushes to GHCR (ghcr.io/cyanautomation/motioninocean:v1.2.3)
# - GitHub Release created with changelog
```

See [.github/workflows/docker-publish.yml](.github/workflows/docker-publish.yml) for automation details.

### Multi-Architecture Builds

Motion In Ocean is locked to **Debian Bookworm** (stable, rigid appliance model). The Dockerfile supports multi-arch via Docker Buildx without suite overrides:

```bash
# Build for arm64 (Raspberry Pi) and amd64 (Intel/AMD)
docker buildx build --platform linux/arm64,linux/amd64 \
  -t ghcr.io/cyanautomation/motioninocean:latest .
```

**Architecture & Philosophy:** Motion In Ocean is an appliance container designed for Raspberry Pi with CSI camera hardware. It locks to Bookworm distro and hardware assumptions for reliability, fail-fast semantics, and minimal operational complexity. If you need alternative distros, fork the Dockerfile and adapt the camera package sources.

---

## PR Guidelines

### Before Submitting

1. **Run all checks locally:**

   ```bash
   make ci
   make audit-ui
   ```

2. **Commit message format:**

   ```
   [<component>] Brief description

   Longer explanation if needed.

   - Bullet point 1
   - Bullet point 2
   ```

   Examples:

   ```
   [webcam] Add JPEG quality setting
   [management] Fix SSRF bypass for private IPs
   [docs] Update deployment guide with multi-host example
   [ci] Add UI tests for management dashboard
   ```

3. **PR title format:**

   ```
   [<component>] Description
   ```

4. **Checklist:**
   - [ ] All tests pass (`make test`)
   - [ ] Code style passes (`make lint`, `make format`, `make type-check`)
   - [ ] Security passes (`make security`)
   - [ ] UI tests pass (if UI changes, `make audit-ui`)
   - [ ] Commits follow format above
   - [ ] No temporary files committed
   - [ ] Documentation updated if behavior changed

### PR Description Template

```markdown
## Summary

[1-2 sentences describing the change]

## Motivation

[Why this change is needed]

## Changes

- [Change 1]
- [Change 2]

## Testing

[How this was tested, manual steps if needed]

## Screenshots (if UI)

[Screenshots of new UI, before/after if applicable]

## Deployment Notes

[Any new env vars, database migrations, etc.]
```

### Review Expectations

- Code must pass CI (linting, types, tests, security)
- Tests required for new functionality
- Documentation updated if applicable
- At least one approving review before merge

---

## Troubleshooting

### Tests Fail Locally But Not in CI

**Possible causes:**

1. Python version mismatch (e.g., local 3.9 vs CI 3.11, 3.12)
2. Missing dev dependencies: `pip install -r requirements-dev.txt`
3. Stale cache: `make clean && make test`
4. Different Docker mount behavior on macOS/Windows

**Fixes:**

```bash
# Verify Python version (should be 3.9+)
python --version

# Reinstall ALL dependencies
pip install -r requirements.txt -r requirements-dev.txt --upgrade --force-reinstall

# Clean cache
make clean

# Run specific test with verbose output
python -m pytest tests/unit/test_feature_flags.py -vvs --tb=short
```

### ModuleNotFoundError When Running Locally

Ensure `.venv` is activated and packages installed:

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### Docker Container Exits Immediately

Check logs:

```bash
docker compose logs --tail=50 motion-in-ocean
```

Common causes:

- Missing `RESOLUTION` setting: Set to `640x480` in `.env`
- Camera device not found: Use mock mode instead (`docker compose -f docker-compose.yml -f docker-compose.mock.yml up`)
- Invalid environment variable: Check against [docs/ENVIRONMENT_VARIABLES_DOCUMENTATION_COMPLETE.md](docs/ENVIRONMENT_VARIABLES_DOCUMENTATION_COMPLETE.md)

### Camera Not Detected on Raspberry Pi

See [.github/skills/pi-camera-troubleshooting/SKILL.md](.github/skills/pi-camera-troubleshooting/SKILL.md) for detailed diagnostics.

---

## Building & Generating Documentation

Motion In Ocean uses automated documentation generation from source code docstrings and JSDoc comments.

### Building Sphinx Documentation (Python)

Generate HTML documentation from Python docstrings using Sphinx with napoleon extension:

```bash
# Build HTML documentation
make docs-build
# Output: docs/_build/html/index.html

# Validate documentation (warnings treated as errors)
make docs-check
# Use in CI to catch broken references and incomplete docstrings

# Clean build artifacts
make docs-clean
```

### Generating JSDoc (JavaScript)

Generate HTML documentation from JavaScript JSDoc comments:

```bash
# Build JSDoc
make jsdoc
# Output: docs/_build/html/js/index.html
```

### Documentation Structure

- **Python API:** Auto-generated from Google-style docstrings in `pi_camera_in_docker/*.py`
- **JavaScript API:** Auto-generated from JSDoc comments in `pi_camera_in_docker/static/js/*.js`
- **Guides:** Manual markdown files in `docs/guides/` (DEPLOYMENT.md, FEATURE_FLAGS.md, etc.)

### Documentation Requirements

When adding new functions/classes:

1. **Python:** Add Google-style docstring with Args, Returns, Raises sections
2. **JavaScript:** Add JSDoc header with @param, @returns, @throws, @async tags
3. **Build locally:** `make docs-check` to validate before pushing
4. **PR checklist:** Ensure "Documentation updated" if behavior changed

See [Code Style Guidelines](#code-style-guidelines) above for examples.

---

## See Also

- [CONTRIBUTING.md](CONTRIBUTING.md) — Human-focused contribution guidelines
- [README.md](README.md) — Quick start, project overview
- [docs/guides/DEPLOYMENT.md](docs/guides/DEPLOYMENT.md) — Deployment patterns and multi-host setup
- [docs/guides/FEATURE_FLAGS.md](docs/guides/FEATURE_FLAGS.md) — Feature flag reference
- [docs/ENVIRONMENT_VARIABLES_DOCUMENTATION_COMPLETE.md](docs/ENVIRONMENT_VARIABLES_DOCUMENTATION_COMPLETE.md) — Complete env var listing
- [Makefile](Makefile) — All available development commands
- [containers/README.md](containers/README.md) — Docker-first deployment directory patterns
