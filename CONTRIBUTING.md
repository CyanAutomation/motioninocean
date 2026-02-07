# Contributing to motion-in-ocean

Thanks for your interest in contributing to **motion-in-ocean**! 🌊📷  
This is a small open-source project focused on making Raspberry Pi CSI camera streaming reliable and easy to deploy in Docker-based homelabs.

Even small contributions (docs fixes, examples, typos) are genuinely appreciated.

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

```bash
docker compose build
docker compose up
````

### Mock camera mode (non-Raspberry Pi)

For development on amd64 systems (no camera), set:

```env
MOCK_CAMERA=true
```

This allows testing of:

* Flask server behaviour
* `/health` and `/ready`
* config and routing

---

## Coding standards

Please keep changes:

* Small and focused
* Easy to understand
* Consistent with the existing style

### Recommendations

* Prefer readability over cleverness
* Avoid new dependencies unless strongly justified
* Add comments where Raspberry Pi quirks require explanation

### Logging style

* Production/operator logs should avoid emoji markers.
* Prefer stable ASCII severity prefixes such as `[INFO]`, `[WARN]`, and `[ERROR]` for machine-readable output.

---

## Commit messages

Please use clear commit messages:

* `docs: clarify docker-compose example`
* `fix: handle missing media devices`
* `feat: add CAMERA_INDEX support`

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

   # Or run all checks at once
   make ci
   ```

5. Validate container builds:

   * container builds successfully
   * endpoints still work (`/health`, `/ready`)

6. Submit a Pull Request with:

   * what changed
   * why it changed
   * how it was tested

If your PR changes behaviour or config, please update the README accordingly.

**Note:** Pre-commit hooks will automatically run basic checks when you commit. The CI pipeline will run comprehensive checks on all PRs.

---

## Reporting bugs

Please include:

* Raspberry Pi model + OS version (`cat /etc/os-release`)
* Camera module type
* `docker-compose.yaml` (device + volume mappings)
* Container logs:

  ```bash
  docker logs motion-in-ocean --tail 200
  ```
* Output of:

  ```bash
  curl http://localhost:8000/health
  curl http://localhost:8000/ready
  ```

---

## Feature requests

Feature requests are welcome, but the project intentionally stays lightweight.

When suggesting a feature, please clarify:

* The real-world homelab use case
* Whether it can be optional (env flag)
* Whether it adds dependencies or complexity

---

## Code of Conduct

This project follows a Code of Conduct. By participating, you agree to uphold it.

See: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
