# Development Setup Guide

This guide will help you set up a development environment for motion-in-ocean.

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Docker and Docker Compose (for container testing)
- Git
- Make (optional, for convenient commands)

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/CyanAutomation/motioninocean.git
cd motioninocean
```

### 2. Set Up Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Development Dependencies

```bash
# Install all development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run only unit tests
pytest tests/ -m unit

# Run only integration tests
pytest tests/ -m integration

# Run with coverage report
pytest --cov=pi_camera_in_docker --cov-report=html tests/
```

### Code Quality Checks

```bash
# Run linting
ruff check pi_camera_in_docker/ tests/

# Auto-fix linting issues
ruff check --fix pi_camera_in_docker/ tests/

# Format code
ruff format pi_camera_in_docker/ tests/

# Run type checking
mypy pi_camera_in_docker/

# Run security checks
bandit -r pi_camera_in_docker/ -c pyproject.toml
```

### Using Make Commands

The project includes a Makefile with convenient commands:

```bash
# Show all available commands
make help

# Install development dependencies
make install-dev

# Run all tests
make test

# Run tests with coverage
make coverage

# Run linting
make lint

# Format code
make format

# Run type checking
make type-check

# Run security checks
make security

# Run all CI checks locally
make ci-check

# Clean up generated files
make clean
```

### Docker Development

```bash
# Build Docker image
docker build -t motion-in-ocean:dev .

# Run container with docker-compose
docker compose up

# Run tests in Docker
docker run --rm -v $(PWD):/app motion-in-ocean:dev pytest tests/
```

## Pre-commit Hooks

Pre-commit hooks are automatically installed when you run `make install-dev` or `pre-commit install`.

These hooks will:
- Check and fix trailing whitespace
- Check and fix file endings
- Validate YAML, JSON, and TOML files
- Run ruff linting and formatting
- Run mypy type checking
- Run bandit security checks
- Validate shell scripts with shellcheck

To run pre-commit hooks manually:

```bash
# Run on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run
```

## Environment Configuration

For local development, create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` to configure:
- `RESOLUTION` - Camera resolution (e.g., 640x480, 1280x720)
- `FPS` - Frame rate (0 = camera default)
- `EDGE_DETECTION` - Enable edge detection (true/false)
- `MOCK_CAMERA` - Use mock camera for development (true/false)
- `JPEG_QUALITY` - JPEG compression quality (1-100)
- `TZ` - Timezone for logging

For development on non-Raspberry Pi machines, set:
```env
MOCK_CAMERA=true
```

## Testing Without Hardware

To test the application without a Raspberry Pi camera:

1. Set `MOCK_CAMERA=true` in your `.env` file
2. Run the application:
   ```bash
   python pi_camera_in_docker/main.py
   ```
3. Access endpoints:
   - http://localhost:8000/ - Main page
   - http://localhost:8000/health - Health check
   - http://localhost:8000/ready - Readiness check
   - http://localhost:8000/metrics - Metrics
   - http://localhost:8000/stream.mjpg - MJPEG stream

## Project Structure

```
motioninocean/
├── pi_camera_in_docker/    # Main application code
│   ├── main.py             # Flask application
│   ├── static/             # Static assets
│   └── templates/          # HTML templates
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── conftest.py         # pytest fixtures
├── .github/                # GitHub Actions workflows
│   └── workflows/
│       ├── test.yml        # Test automation
│       └── docker-publish.yml  # Docker publishing
├── pyproject.toml          # Python project configuration
├── .pre-commit-config.yaml # Pre-commit hooks configuration
├── Makefile                # Development commands
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── Dockerfile              # Docker image definition
└── docker-compose.yml      # Docker Compose configuration
```

## Troubleshooting

### Import Errors

If you see import errors, ensure:
1. Virtual environment is activated
2. Dependencies are installed: `pip install -r requirements-dev.txt`
3. You're running commands from the project root

### Test Failures

If tests fail:
1. Check that you're using Python 3.10+: `python --version`
2. Reinstall dependencies: `pip install -r requirements-dev.txt`
3. Run tests with verbose output: `pytest tests/ -v`

### Docker Build Issues

If Docker builds fail:
1. Ensure Docker is running: `docker ps`
2. Check available disk space: `df -h`
3. Clean up old images: `docker system prune`

### Pre-commit Hook Failures

If pre-commit hooks fail:
1. Run manually to see errors: `pre-commit run --all-files`
2. Fix issues automatically: `make format`
3. Reinstall hooks: `pre-commit uninstall && pre-commit install`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## Getting Help

- Open an issue on GitHub
- Check existing documentation in the repository
- Review the README.md for project overview
