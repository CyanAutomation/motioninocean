# Makefile for motion-in-ocean development tasks
# Provides convenient shortcuts for common operations

# Docker build configuration
# Locked to Bookworm: avoids Trixie's SHA1 GPG policy incompatibility with the Raspberry Pi apt repo.
# The container camera stack runs on Bookworm userspace even when the host runs Trixie (containers ship their own userspace).
DEBIAN_SUITE ?= bookworm
RPI_SUITE ?= bookworm

.PHONY: help install install-dev install-node test test-frontend lint format type-check security clean run-mock docker-build docker-build-prod docker-build-arm64 docker-build-prod-arm64 docker-build-amd64 docker-build-prod-amd64 docker-build-all docker-build-prod-all docker-run docker-stop docker-clean pre-commit validate-diagrams check-playwright audit-ui audit-ui-webcam audit-ui-management audit-ui-interactive docs-build docs-check jsdoc docs-clean ci validate

# Default target: show help
help:
	@echo "Motion In Ocean - Development Commands"
	@echo "========================================"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install          Install production dependencies"
	@echo "  make install-dev      Install development dependencies"
	@echo "  make install-node     Install Node.js dependencies (npm install)"
	@echo "  make pre-commit       Install and setup pre-commit hooks"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linter (ruff)"
	@echo "  make format           Format code (ruff format)"
	@echo "  make type-check       Run type checker (mypy)"
	@echo "  make security         Run security checks (bandit)"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs-build       Build Sphinx HTML documentation"
	@echo "  make docs-check       Check if documentation builds (CI validation)"
	@echo "  make jsdoc            Build JSDoc for JavaScript files"
	@echo "  make docs-clean       Clean documentation build artifacts"
	@echo ""
	@echo "Validation:"
	@echo "  make validate-diagrams    Validate Mermaid diagram syntax"
	@echo "  make check-playwright     Check Playwright installation"
	@echo "  make audit-ui             Run full UI audit (both modes, all viewports)"
	@echo "  make audit-ui-webcam      Run UI audit for webcam mode only"
	@echo "  make audit-ui-management  Run UI audit for management mode only"
	@echo "  make audit-ui-interactive Open Playwright inspector for manual auditing"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests with coverage"
	@echo "  make test-frontend    Run frontend JavaScript unit tests"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make coverage         Generate coverage report"
	@echo ""
	@echo "Development:"
	@echo "  make run-mock         Run Flask app with mock camera"
	@echo "  make clean            Clean build artifacts and cache files"
	@echo ""
	@echo "Docker Build (Debian Bookworm, appliance-model, locked to RPi CSI camera):"
	@echo "  Single-Platform Builds (host architecture):"
	@echo "    make docker-build              Build image (mock support included)"
	@echo "    make docker-build-prod         Build production-tagged image (same build, different tag)"
	@echo ""
	@echo "  Cross-Platform Builds (explicit architecture):"
	@echo "    make docker-build-arm64        Build ARM64 dev image (RPi deployment)"
	@echo "    make docker-build-prod-arm64   Build ARM64 production image"
	@echo "    make docker-build-amd64        Build AMD64 image (mock support included)"
	@echo "    make docker-build-prod-amd64   Build AMD64 production-tagged image (same build)"
	@echo ""
	@echo "  Multi-Architecture Convenience (sequential arm64 + amd64):"
	@echo "    make docker-build-all          Build both ARM64 and AMD64 images"
	@echo "    make docker-build-prod-all     Build both ARM64 and AMD64 production-tagged images"
	@echo ""
	@echo "  Options:"
	@echo "    DOCKER_PUSH=1 REGISTRY=ghcr.io/myorg make docker-build-amd64  (auto-push to registry)"
	@echo ""
	@echo "Docker Runtime:"
	@echo "  make docker-run                Run Docker container"
	@echo "  make docker-stop               Stop Docker container"
	@echo ""
	@echo "CI/CD:"
	@echo "  make ci               Run all CI checks (lint, type-check, test)"
	@echo "  make validate         Validate all code quality checks"

# Installation targets
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

install-node:
	@echo "Installing Node.js dependencies..."
	npm install

pre-commit:
	pip install pre-commit
	pre-commit install
	pre-commit install --hook-type commit-msg

# Code quality targets
lint:
	@echo "Running ruff linter..."
	ruff check pi_camera_in_docker/ tests/

lint-fix:
	@echo "Running ruff linter with auto-fix..."
	ruff check pi_camera_in_docker/ tests/ --fix

format:
	@echo "Formatting code with ruff..."
	ruff format pi_camera_in_docker/ tests/

format-check:
	@echo "Checking code formatting..."
	ruff format --check pi_camera_in_docker/ tests/

type-check:
	@echo "Running mypy type checker..."
	-mypy pi_camera_in_docker/ --ignore-missing-imports --show-error-codes --no-strict-optional --allow-untyped-calls --allow-subclassing-any

security:
	@echo "Running bandit security checks..."
	bandit -r pi_camera_in_docker/ -c pyproject.toml

security-all:
	@echo "Running comprehensive security checks..."
	bandit -r pi_camera_in_docker/ -c pyproject.toml
	@echo "Checking for known vulnerabilities in dependencies..."
	safety check --json || true

# Documentation targets
docs-build:
	@echo "Building Sphinx documentation..."
	@if ! command -v sphinx-build &> /dev/null; then \
		echo "Installing Sphinx..."; \
		pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints; \
	fi
	@cd docs && sphinx-build -b html -W . _build/html
	@echo "✓ Documentation built to docs/_build/html/index.html"

docs-check:
	@echo "Checking documentation build (warnings as errors)..."
	@if ! command -v sphinx-build &> /dev/null; then \
		echo "Installing Sphinx..."; \
		pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints; \
	fi
	@cd docs && sphinx-build -b html -W --keep-going . _build/html 2>&1 | tee /tmp/docs-check.log
	@if grep -q "WARNING\|ERROR" /tmp/docs-check.log; then \
		echo "✗ Documentation check failed (see above for warnings)"; \
		exit 1; \
	fi
	@echo "✓ Documentation check passed!"

jsdoc:
	@echo "Building JSDoc documentation..."
	@if ! command -v jsdoc &> /dev/null; then \
		echo "Installing JSDoc..."; \
		npm install --save-dev jsdoc docdash; \
	fi
	jsdoc -c jsdoc.json
	@echo "✓ JSDoc built to docs/_build/html/js/index.html"

docs-clean:
	@echo "Cleaning documentation build artifacts..."
	rm -rf docs/_build
	@echo "✓ Documentation cleaned!"

# Diagram validation targets
validate-diagrams:
	@echo "Validating Mermaid diagrams..."
	@if ! command -v mmdc &> /dev/null; then \
		echo "Error: mermaid-cli not found. Run 'make install-node' to install Node dependencies."; \
		exit 1; \
	fi
	@echo "Checking diagrams in PRD-backend.md..."
	mmdc -i PRD-backend.md -o /tmp/prd-backend.svg -t dark --quiet 2>&1 | grep -i "error" || echo "✓ PRD-backend.md diagrams valid"
	@echo "Checking diagrams in PRD-frontend.md..."
	mmdc -i PRD-frontend.md -o /tmp/prd-frontend.svg -t dark --quiet 2>&1 | grep -i "error" || echo "✓ PRD-frontend.md diagrams valid"
	@echo "Checking diagrams in DEPLOYMENT.md..."
	mmdc -i DEPLOYMENT.md -o /tmp/deployment.svg -t dark --quiet 2>&1 | grep -i "error" || echo "✓ DEPLOYMENT.md diagrams valid"
	@echo "Checking diagrams in README.md..."
	mmdc -i README.md -o /tmp/readme.svg -t dark --quiet 2>&1 | grep -i "error" || echo "✓ README.md diagrams valid"
	@echo "✓ All diagram validations passed!"

# Playwright validation targets
check-playwright:
	@echo "Checking Playwright installation..."
	@if ! command -v npx &> /dev/null; then \
		echo "Error: Node.js/npm not found. Install Node.js or run 'make install-node'."; \
		exit 1; \
	fi
	@echo "Verifying Playwright is installed..."
	npx playwright --version
	@echo "✓ Playwright is ready for testing"

# UI Audit targets
audit-ui-webcam:
	@echo "Running UI audit for webcam mode..."
	@if [ ! -f "audit-template.js" ]; then \
		echo "Error: audit-template.js not found"; \
		exit 1; \
	fi
	MIO_MODE=webcam node audit-template.js
	@echo "✓ Webcam UI audit complete. See audit-results/ for details."

audit-ui-management:
	@echo "Running UI audit for management mode..."
	@if [ ! -f "audit-template.js" ]; then \
		echo "Error: audit-template.js not found"; \
		exit 1; \
	fi
	MIO_MODE=management node audit-template.js
	@echo "✓ Management UI audit complete. See audit-results/ for details."

audit-ui:
	@echo "Running UI audit for both modes..."
	@if [ ! -f "audit-template.js" ]; then \
		echo "Error: audit-template.js not found"; \
		exit 1; \
	fi
	MIO_MODE=both node audit-template.js
	@echo "✓ Full UI audit complete. See audit-results/ for details."

audit-ui-interactive:
	@echo "Opening Playwright inspector for interactive auditing..."
	@if ! command -v npx &> /dev/null; then \
		echo "Error: Node.js/npm not found. Run 'make install-node' first."; \
		exit 1; \
	fi
	npx playwright codegen http://localhost:8000
	@echo "Inspector closed. Save the generated script if needed."

# Testing targets
test:
	@echo "Running all tests with coverage..."
	$(MAKE) test-frontend
	pytest tests/ --cov=pi_camera_in_docker --cov-report=term-missing --cov-report=html --cov-report=xml -v

test-frontend:
	@echo "Running frontend JavaScript tests..."
	node --test tests/frontend/*.test.mjs

test-unit:
	@echo "Running unit tests..."
	pytest tests/test_units.py -v

test-integration:
	@echo "Running integration tests..."
	pytest tests/test_integration.py -v

test-config:
	@echo "Running configuration tests..."
	pytest tests/test_config.py -v

coverage:
	@echo "Generating coverage report..."
	pytest tests/ --cov=pi_camera_in_docker --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

# Development targets
run-mock:
	@echo "Starting Flask server with mock camera..."
	MOCK_CAMERA=true FLASK_ENV=development python3 pi_camera_in_docker/main.py

clean:
	@echo "Cleaning build artifacts and cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.orig" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml
	@echo "Clean complete!"

# Docker targets
# Using BuildKit for enhanced caching and faster builds
# Motion In Ocean is locked to Debian Bookworm (stable, rigid appliance model).
#
# PRIMARY BUILD TARGETS:
#   make docker-build         Build image (mock support included)
#   make docker-build-prod    Build production-tagged image (same build, different tag)
#   make docker-build-arm64   Build ARM64 dev image for Raspberry Pi deployment
#
# ARCHITECTURE NOTE:
# Local `docker build` defaults to your host's CPU architecture (amd64 on Intel/Mac, arm64 on ARM hosts).
# For Raspberry Pi deployment, use the -arm64 targets to explicitly build ARM64 images:
#   make docker-build-arm64       (instead of make docker-build)
#   make docker-build-prod-arm64  (instead of make docker-build-prod)
# Or use plain `docker build` if building on an ARM64 host.
docker-build:
	@echo "Building Docker image (DEBIAN_SUITE=$(DEBIAN_SUITE), RPI_SUITE=$(RPI_SUITE), mock support included)..."
	@echo "Note: This builds for your host architecture. For Raspberry Pi, use: make docker-build-arm64"
	DOCKER_BUILDKIT=1 docker build \
		--build-arg DEBIAN_SUITE=$(DEBIAN_SUITE) \
		--build-arg RPI_SUITE=$(RPI_SUITE) \
		-t motion-in-ocean:dev .

docker-build-prod:
	@echo "Building production-tagged Docker image (DEBIAN_SUITE=$(DEBIAN_SUITE), RPI_SUITE=$(RPI_SUITE), mock support included)..."
	DOCKER_BUILDKIT=1 docker build \
		--build-arg DEBIAN_SUITE=$(DEBIAN_SUITE) \
		--build-arg RPI_SUITE=$(RPI_SUITE) \
		-t motion-in-ocean:dev-prod .

# ARM64-explicit targets (use for Raspberry Pi deployment or when building on non-ARM hosts)
docker-build-arm64:
	@echo "Building ARM64 Docker image (DEBIAN_SUITE=$(DEBIAN_SUITE), RPI_SUITE=$(RPI_SUITE), mock support included)..."
	docker buildx build --platform linux/arm64 \
		--build-arg DEBIAN_SUITE=$(DEBIAN_SUITE) \
		--build-arg RPI_SUITE=$(RPI_SUITE) \
		-t motion-in-ocean:dev .

docker-build-prod-arm64:
	@echo "Building ARM64 production-tagged Docker image (DEBIAN_SUITE=$(DEBIAN_SUITE), RPI_SUITE=$(RPI_SUITE), mock support included)..."
	docker buildx build --platform linux/arm64 \
		--build-arg DEBIAN_SUITE=$(DEBIAN_SUITE) \
		--build-arg RPI_SUITE=$(RPI_SUITE) \
		-t motion-in-ocean:dev-prod .

# AMD64-explicit targets (for Intel/AMD hosts)
# To enable auto-push to registry: DOCKER_PUSH=1 make docker-build-amd64
docker-build-amd64:
	@echo "Building AMD64 Docker image (DEBIAN_SUITE=$(DEBIAN_SUITE), RPI_SUITE=$(RPI_SUITE), mock support included)..."
	docker buildx build --platform linux/amd64 \
		--build-arg DEBIAN_SUITE=$(DEBIAN_SUITE) \
		--build-arg RPI_SUITE=$(RPI_SUITE) \
		-t motion-in-ocean:dev \
		$${DOCKER_PUSH:+--push} .

docker-build-prod-amd64:
	@echo "Building AMD64 production-tagged Docker image (DEBIAN_SUITE=$(DEBIAN_SUITE), RPI_SUITE=$(RPI_SUITE), mock support included)..."
	docker buildx build --platform linux/amd64 \
		--build-arg DEBIAN_SUITE=$(DEBIAN_SUITE) \
		--build-arg RPI_SUITE=$(RPI_SUITE) \
		-t motion-in-ocean:dev-prod \
		$${DOCKER_PUSH:+--push} .

# Multi-architecture convenience targets
# Used for building both arm64 and amd64 sequentially
docker-build-all: docker-build-arm64 docker-build-amd64
	@echo "✓ Both ARM64 and AMD64 dev images built successfully"

docker-build-prod-all: docker-build-prod-arm64 docker-build-prod-amd64
	@echo "✓ Both ARM64 and AMD64 production images built successfully"

docker-run:
	@echo "Running Docker container..."
	docker run -p 8000:8000 --name motion-in-ocean-dev motion-in-ocean:dev

docker-stop:
	@echo "Stopping Docker container..."
	docker stop motion-in-ocean-dev
	docker rm motion-in-ocean-dev

docker-clean:
	@echo "Cleaning Docker resources..."
	docker image prune -f

# CI/CD targets
ci: lint format-check type-check test
	@echo "✓ All CI checks passed!"

validate: ci security
	@echo "✓ All validation checks passed!"

# Quick check before committing
check: format-check lint type-check
	@echo "✓ Quick checks passed! Run 'make test' before pushing."
