# Chef Agent Makefile

.PHONY: help install test lint format migrate seed clean run dev mcp-server

# Default target
help:
	@echo "Available commands:"
	@echo "  install    - Install dependencies"
	@echo "  test       - Run tests"
	@echo "  lint       - Run linters"
	@echo "  format     - Format code"
	@echo "  migrate    - Run database migrations"
	@echo "  seed       - Seed database with sample recipes"
	@echo "  clean      - Clean temporary files"
	@echo "  run        - Run the application"
	@echo "  dev        - Run in development mode"
	@echo "  mcp-server - Run MCP server"

# Install dependencies
install:
	poetry install

# Run tests
test:
	poetry run pytest tests/ -v

# Run linters
lint:
	poetry run flake8 .
	poetry run black --check .
	poetry run isort --check-only .

# Format code
format:
	poetry run black .
	poetry run isort .

# Run database migrations
migrate:
	poetry run python -m scripts.migrate

# Show migration status
migrate-status:
	poetry run python -m scripts.migrate --status

# Seed database with sample recipes
seed:
	poetry run python -m scripts.ingest_recipes data/recipes_sample.json

# Generate SQL migration from recipes
seed-sql:
	poetry run python -m scripts.ingest_recipes data/recipes_sample.json --output migrations/0002_seed_recipes.sql

# Clean temporary files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	rm -f *.db *.sqlite *.sqlite3

# Run the application
run:
	poetry run uvicorn main:app --host 0.0.0.0 --port 8000

# Run in development mode
dev:
	API_RELOAD=true poetry run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Setup development environment
setup: install migrate seed
	@echo "Development environment ready!"
	@echo "Run 'make dev' to start the development server"

# Full test suite
test-all: lint test
	@echo "All tests passed!"

# Production build
build:
	docker build -t chef-agent .

# Run with Docker
docker-run:
	docker-compose up --build

# Demo (record terminal session)
demo:
	@echo "Starting Chef Agent demo..."
	@echo "1. Testing health endpoint..."
	curl -s http://localhost:8000/health | jq . || echo "Server not running, starting..."
	@echo "2. Testing rate limiting..."
	@echo "Making 12 requests (limit is 10/min):"
	@for i in {1..12}; do echo -n "Request $$i: "; curl -s http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo "Rate limited"; done
	@echo "3. Testing security headers..."
	curl -I http://localhost:8000/health 2>/dev/null | grep -E "(X-|Strict-|Content-Security)" || echo "Headers check completed"
	@echo "Demo completed! 🎉"

# Run MCP server
mcp-server:
	@echo "Starting MCP server..."
	poetry run python -m scripts.run_mcp_server
