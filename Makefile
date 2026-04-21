# Makefile for TTS System

.PHONY: help install dev run test lint format clean docker-build docker-run migrate

help: ## Show this help message
	@echo "TTS System - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync

dev: ## Install development dependencies
	uv sync --all-extras

run: ## Run development server
	@bash -c 'source .env 2>/dev/null || true; uv run uvicorn packages.api.main:app --reload --host 0.0.0.0 --port $${API_PORT:-8000}'

prod: ## Run production server
	@bash -c 'source .env 2>/dev/null || true; uv run uvicorn packages.api.main:app --host 0.0.0.0 --port $${API_PORT:-8000} --workers 4'

test: ## Run tests
	uv run pytest tests/ -v

test-cov: ## Run tests with coverage
	uv run pytest tests/ -v --cov=packages --cov-report=html --cov-report=term

lint: ## Run linter
	uv run ruff check packages/ tests/

format: ## Format code
	uv run black packages/ tests/
	uv run ruff check --fix packages/ tests/

type-check: ## Run type checker
	uv run mypy packages/

migrate: ## Run database migrations
	uv run alembic upgrade head

migrate-create: ## Create new migration
	@read -p "Enter migration message: " msg; \
	uv run alembic revision --autogenerate -m "$$msg"

clean: ## Clean up cache and temporary files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/

docker-build: ## Build Docker image
	docker build -t tts-system:latest .

docker-run: ## Run Docker container
	@bash -c 'source .env 2>/dev/null || true; docker run -d --name tts-api -p $${API_PORT:-8000}:$${API_PORT:-8000} \
		-e API_PORT=$${API_PORT:-8000} \
		-v $$(pwd)/storage:/app/storage \
		-v $$(pwd)/database:/app/database \
		tts-system:latest'

docker-stop: ## Stop Docker container
	docker stop tts-api
	docker rm tts-api

docker-compose-up: ## Start with docker-compose
	docker-compose up -d

docker-compose-down: ## Stop docker-compose
	docker-compose down

docker-logs: ## View docker logs
	docker-compose logs -f

quickstart: ## Quick start (install + migrate + run)
	python scripts/quickstart.py

setup: ## Initial setup
	@echo "Setting up TTS System..."
	uv sync
	cp .env.example .env
	@echo "Created .env file - please configure your API keys"
	mkdir -p storage/cache storage/temp database
	uv run alembic upgrade head
	@echo "Setup complete! Run 'make run' to start the server."
