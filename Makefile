.PHONY: help install install-dev test test-unit test-integration coverage lint format type-check security pre-commit clean docker-build docker-run

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements-dev.txt
	pre-commit install

test: ## Run all tests
	pytest tests/ -v

test-unit: ## Run unit tests only
	pytest tests/unit/ -v -m unit

test-integration: ## Run integration tests only
	pytest tests/integration/ -v -m integration

coverage: ## Run tests with coverage report
	pytest --cov=pi_camera_in_docker --cov-report=html --cov-report=term tests/
	@echo "Coverage report generated in htmlcov/index.html"

lint: ## Run code linting
	ruff check pi_camera_in_docker/ tests/

format: ## Format code with ruff
	ruff format pi_camera_in_docker/ tests/
	ruff check --fix pi_camera_in_docker/ tests/

type-check: ## Run type checking
	mypy pi_camera_in_docker/

security: ## Run security checks
	bandit -r pi_camera_in_docker/ -c pyproject.toml
	safety check --file requirements.txt --file requirements-dev.txt

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

docker-build: ## Build Docker image
	docker build -t motion-in-ocean:dev .

docker-run: ## Run Docker container in development mode
	docker compose up

docker-test: ## Run tests in Docker environment
	docker run --rm -v $(PWD):/app motion-in-ocean:dev pytest tests/

ci-check: ## Run all CI checks locally
	@echo "Running format check..."
	ruff format --check pi_camera_in_docker/ tests/
	@echo "Running linting..."
	ruff check pi_camera_in_docker/ tests/
	@echo "Running type checking..."
	mypy pi_camera_in_docker/
	@echo "Running tests..."
	pytest tests/ -v
	@echo "Running security checks..."
	bandit -r pi_camera_in_docker/ -c pyproject.toml
	@echo "All CI checks passed!"

dev-setup: install-dev ## Complete development environment setup
	@echo "Development environment setup complete!"
	@echo "Run 'make help' to see available commands"
