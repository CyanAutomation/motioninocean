# Makefile for motion-in-ocean development tasks
# Provides convenient shortcuts for common operations

.PHONY: help install install-dev test lint format type-check security clean run-mock docker-build docker-run pre-commit

# Default target: show help
help:
	@echo "Motion In Ocean - Development Commands"
	@echo "========================================"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install          Install production dependencies"
	@echo "  make install-dev      Install development dependencies"
	@echo "  make pre-commit       Install and setup pre-commit hooks"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linter (ruff)"
	@echo "  make format           Format code (ruff format)"
	@echo "  make type-check       Run type checker (mypy)"
	@echo "  make security         Run security checks (bandit)"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests with coverage"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make coverage         Generate coverage report"
	@echo ""
	@echo "Development:"
	@echo "  make run-mock         Run Flask app with mock camera"
	@echo "  make clean            Clean build artifacts and cache files"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build          Build default image (with mock camera)"
	@echo "  make docker-build-prod     Build production image (without mock camera)"
	@echo "  make docker-build-production  Build production image (opencv, no mock)"
	@echo "  make docker-build-all      Build all image variants"
	@echo "  make docker-run            Run Docker container"
	@echo "  make docker-stop           Stop Docker container"
	@echo ""
	@echo "CI/CD:"
	@echo "  make ci               Run all CI checks (lint, type-check, test)"
	@echo "  make validate         Validate all code quality checks"

# Installation targets
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

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

# Testing targets
test:
	@echo "Running all tests with coverage..."
	pytest tests/ --cov=pi_camera_in_docker --cov-report=term-missing --cov-report=html --cov-report=xml -v

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
docker-build:
	@echo "Building default Docker image (with mock camera)..."
	DOCKER_BUILDKIT=1 docker build --build-arg INCLUDE_MOCK_CAMERA=true -t motion-in-ocean:dev .

docker-build-prod:
	@echo "Building production Docker image (without mock camera, smallest size)..."
	DOCKER_BUILDKIT=1 docker build --build-arg INCLUDE_MOCK_CAMERA=false -t motion-in-ocean:dev-prod .

# Legacy target for backward compatibility
docker-build-both: docker-build docker-build-full

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
