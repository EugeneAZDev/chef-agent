# Chef Agent Makefile

.PHONY: help test test-fast test-integration test-security test-performance test-all install dev lint format clean

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	poetry install

dev: ## Install development dependencies
	poetry install --with dev

test: ## Run all tests except performance
	poetry run pytest tests/ -m "not performance" -v

test-fast: ## Run only fast unit tests
	poetry run pytest tests/test_*.py -m "not performance and not integration and not security" -v

test-integration: ## Run integration tests
	poetry run pytest tests/ -m "integration" -v

test-security: ## Run security tests
	poetry run pytest tests/ -m "security" -v

test-performance: ## Run performance tests (slow)
	poetry run pytest tests/ -m "performance" -v

test-all: ## Run all tests including performance
	poetry run pytest tests/ -v

lint: ## Run linting
	poetry run flake8 .
	poetry run black --check .
	poetry run isort --check-only .

format: ## Format code
	poetry run black .
	poetry run isort .
	poetry run pre-commit run --all-files

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov

run: ## Run the application
	poetry run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

run-prod: ## Run the application in production mode
	poetry run uvicorn main:app --host 0.0.0.0 --port 8000

check: lint test ## Run linting and tests

check-all: ## Check all files in the project (including untracked)
	python scripts/check_all.py

check-staged: ## Check only staged files (pre-commit style)
	poetry run pre-commit run --files $(shell git diff --cached --name-only --diff-filter=ACMR | tr '\n' ' ')
