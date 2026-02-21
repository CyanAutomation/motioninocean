# Contributing to motion-in-ocean

Thanks for your interest in contributing to **motion-in-ocean**! 🌊📷  
This is a small open-source project focused on making Raspberry Pi CSI camera streaming reliable and easy to deploy in Docker-based homelabs.

Even small contributions (docs fixes, examples, typos) are genuinely appreciated.

---

## Documentation map

Project documentation is organized under `docs/`:

- Operational guides: [`docs/guides/`](docs/guides/)
- Product requirements: [`docs/product/`](docs/product/)
- Dated reports and analysis: [`docs/reports/`](docs/reports/)
- Testing docs: [`docs/testing/`](docs/testing/)

When changing behavior or configuration, update the relevant document under `docs/` and keep root-level entry docs minimal.

---

## Ways to contribute

You can help by:

- Improving documentation (README, examples, deployment notes)
- Adding homelab integration examples (Home Assistant, OctoPrint, Uptime Kuma, Homepage, etc.)
- Improving device discovery / mapping reliability across Pi models
- Adding CI/CD workflows (multi-arch builds, release tagging)
- Bug fixes and small feature improvements
- Reporting bugs with clear logs and reproduction steps

---

## Before you start

Please check:

- Existing issues (you may find your idea already tracked)
- Project goals in the README
- Any open PRs that might overlap

If you're unsure whether a change will be accepted, open an issue first to discuss it.

---

## Development workflow

### Prerequisites

- Python 3.9+ (3.11+ recommended)
- Docker + Docker Compose
- Raspberry Pi OS (Bookworm) + ARM64 recommended for real camera testing
- Non-Pi systems are supported for API/dev work using mock mode

### Initial setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/CyanAutomation/motioninocean.git
   cd motioninocean
   ```

2. **Install development dependencies:**

   ```bash
   # Create a virtual environment (recommended)
   python3 -m venv .venv
   source .venv/bin/activate

   # Install dependencies
   pip install -r requirements-dev.txt
   ```

3. **Install pre-commit hooks:**

   ```bash
   make pre-commit
   # or manually:
   pre-commit install
   ```

### Development commands

We provide a `Makefile` with convenient shortcuts for common tasks:

```bash
# View all available commands
make help

# Code quality checks
make lint              # Run linter
make format            # Format code
make type-check        # Run type checker
make security          # Run security checks

# Testing
make test              # Run all tests with coverage
make test-unit         # Run unit tests only
make coverage          # Generate HTML coverage report

# Development
make run-mock          # Run Flask app with mock camera
make clean             # Clean build artifacts

# CI validation
make ci                # Run all CI checks (lint, type-check, test)
make validate          # Run all validation checks including security
```

### Local build & run

**Via Docker Compose:**
```bash
docker compose build
docker compose up
```

**Building for Raspberry Pi (ARM64 hosts):**
If you're building on non-ARM hardware (Intel Mac, x86_64 Linux) for deployment to Raspberry Pi, use the explicit ARM64 targets:
```bash
make docker-build-arm64
```
This ensures Raspberry Pi-specific camera packages are correctly resolved. See [README.md#building-for-raspberry-pi-arm64](README.md#building-for-raspberry-pi-arm64) for details.

### Mock camera mode (non-Raspberry Pi)

For development on amd64 systems (no camera), set:

```env
MOCK_CAMERA=true
```

This allows testing of:

- Flask server behaviour
- `/health` and `/ready`
- config and routing

---

## Coding standards

Please keep changes:

- Small and focused
- Easy to understand
- Consistent with the existing style

### Recommendations

- Prefer readability over cleverness
- Avoid new dependencies unless strongly justified
- Add comments where Raspberry Pi quirks require explanation

### Documentation standards

All new code must include comprehensive docstrings and JSDoc headers. Use the quick reference at [docs/DOCUMENTATION_GUIDE.md](docs/DOCUMENTATION_GUIDE.md) for examples and validation commands.

#### Python Documentation (Google-Style Docstrings)

**Required for:**

- All public functions and methods
- All public classes
- Private methods/functions with > 5 lines of code
- All module-level docstrings

**Components:**

- Brief one-line description
- Detailed explanation (if needed)
- `Args`: Parameter names, types, descriptions
- `Returns`: Type and description
- `Raises`: Exception types and conditions
- `Examples` or `Notes`: For complex logic

**Reference files with examples:**

- [pi_camera_in_docker/management_api.py](pi_camera_in_docker/management_api.py) — REST endpoints, node management
- [pi_camera_in_docker/settings_api.py](pi_camera_in_docker/settings_api.py) — Configuration endpoints
- [pi_camera_in_docker/runtime_config.py](pi_camera_in_docker/runtime_config.py) — Configuration loading
- [pi_camera_in_docker/modes/webcam.py](pi_camera_in_docker/modes/webcam.py) — Camera streaming implementation

**Example:**

```python
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
```

#### JavaScript Documentation (JSDoc)

**Required for:**

- All public functions
- All classes and constructors
- Private functions/methods with > 10 lines of code
- All module-level headers

**Components:**

- Brief description (inline or @description)
- `@param {type}` — Parameter type and description
- `@returns {type}` — Return type and description
- `@throws` — Exception types that can be raised
- `@async` — For async functions
- `@private` — For internal use only

**Reference files with examples:**

- [pi_camera_in_docker/static/js/app.js](pi_camera_in_docker/static/js/app.js) — Streaming viewer logic
- [pi_camera_in_docker/static/js/management.js](pi_camera_in_docker/static/js/management.js) — Node management dashboard
- [pi_camera_in_docker/static/js/settings.js](pi_camera_in_docker/static/js/settings.js) — Settings form handling

**Example:**

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

#### Validation & Resources

Build and validate documentation locally before pushing:

```bash
# Check documentation builds without warnings (CI validation)
make docs-check

# Build full HTML documentation from docstrings
make docs-build

# Build JSDoc for JavaScript
make jsdoc

# Clean build artifacts
make docs-clean
```

**Quick reference:** [docs/DOCUMENTATION_GUIDE.md](docs/DOCUMENTATION_GUIDE.md) — Complete examples, patterns, and checklist

**Full guidelines:** [AGENTS.md#documentation-requirements](AGENTS.md#documentation-requirements) — Detailed rules and style conventions

### Logging style

- Production/operator logs should avoid emoji markers.
- Prefer stable ASCII severity prefixes such as `[INFO]`, `[WARN]`, and `[ERROR]` for machine-readable output.

### Diagramming guidelines

When documenting architecture, workflows, or state transitions (especially in PRDs and deployment docs), use Mermaid diagrams embedded in markdown for clarity. Diagrams render natively in GitHub and greatly help both developers and operators understand complex interactions.

**Guidelines:**

- Refer to [`.github/skills/mermaid-creator/SKILL.md`](.github/skills/mermaid-creator/SKILL.md) for detailed instructions and examples specific to motion-in-ocean.
- Keep diagrams close to the text they clarify (same section).
- Use accurate terminology from PRDs (e.g., `/ready`, `MAX_FRAME_AGE_SECONDS`, `recording_started`, `Bearer Token Auth`).
- Validate Mermaid syntax at [mermaid.live](https://mermaid.live) before committing.
- Include a 2–4 line rationale below each diagram explaining the diagram type and key insight.

Common diagram types in this project:

- **State machines** (`stateDiagram-v2`) — Health/readiness transitions, camera lifecycle.
- **Architecture flowcharts** (`graph TD`) — Multi-host deployment, system components.
- **Sequence diagrams** (`sequenceDiagram`) — API workflows, node registry CRUD.
- **Data flow diagrams** (`graph LR`) — Frame capture pipeline, stream to endpoints.

### UI auditing guidelines

When changes touch the web UI (HTML, CSS, JavaScript, form interactions, responsiveness), perform or request a UI audit to validate design, layout, accessibility, and user workflows across device sizes.

**Guidelines:**

- Refer to [`.github/skills/ui-playwright/SKILL.md`](.github/skills/ui-playwright/SKILL.md) for comprehensive UI auditing methodology using Playwright.
- Test both **webcam mode** (streaming viewer) and **management mode** (node registry) if applicable.
- Validate responsive design at three breakpoints: desktop (>1024px), tablet (768-1024px), mobile (<480px).
- Check accessibility: keyboard navigation, ARIA labels, color contrast, focus states.
- Explore error scenarios: network failures, validation errors, stale streams, edge cases.
- Capture evidence: screenshots at each viewport and state for findings.
- Generate structured audit report (markdown with findings, severity, recommendations).

Common audit scenarios:

- **Before PR merge:** Validate UI changes don't break responsive layout, accessibility, or workflows.
- **Component updates:** Check button sizing, form labels, color/contrast, error messaging.
- **Responsive changes:** Test at mobile, tablet, desktop breakpoints.
- **Feature additions:** Validate new form fields, controls, status indicators, interactions.

**Execution:**

```bash
# Local audit (interactive)
npx playwright codegen http://localhost:8000  # generates recording of interactions

# Docker-based audit
docker compose --profile webcam -e MOCK_CAMERA=true up
# In another terminal:
node audit-script.js  # runs audit workflow, captures screenshots
```

---

## Commit messages

Please use clear commit messages:

- `docs: clarify docker-compose example`
- `fix: handle missing media devices`
- `feat: add CAMERA_INDEX support`

---

## Pull Request process

1. Fork the repository
2. Create a branch:

   ```bash
   git checkout -b feat/my-change
   ```

3. Make your changes
4. Run code quality checks:

   ```bash
   # Format code
   make format

   # Run linter
   make lint

   # Run type checker
   make type-check

   # Run tests
   make test

   # Validate documentation
   make docs-check

   # Or run all checks at once
   make ci
   ```

5. Validate container builds:
   - container builds successfully
   - endpoints still work (`/health`, `/ready`)

6. Submit a Pull Request with:
   - what changed
   - why it changed
   - how it was tested

If your PR changes behaviour, config, or adds new public functions, please ensure:

- Documentation (docstrings/JSDoc) is updated
- README and relevant docs in `docs/` are updated
- Documentation builds without warnings (`make docs-check`)

**Note:** Pre-commit hooks will automatically run basic checks when you commit. The CI pipeline will run comprehensive checks on all PRs.

---

## Reporting bugs

Please include:

- Raspberry Pi model + OS version (`cat /etc/os-release`)
- Camera module type
- `docker-compose.yaml` (device + volume mappings)
- Container logs:

  ```bash
  docker logs motion-in-ocean --tail 200
  ```

- Output of:

  ```bash
  curl http://localhost:8000/health
  curl http://localhost:8000/ready
  ```

---

## Feature requests

Feature requests are welcome, but the project intentionally stays lightweight.

When suggesting a feature, please clarify:

- The real-world homelab use case
- Whether it can be optional (env flag)
- Whether it adds dependencies or complexity

---

## Code of Conduct

This project follows a Code of Conduct. By participating, you agree to uphold it.

See: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
