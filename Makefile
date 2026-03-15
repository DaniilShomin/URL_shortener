.PHONY: help install dev test lint format clean docker-up docker-down docker-logs run migrate

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies with UV"
	@echo "  make dev           - Install dev dependencies"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code"
	@echo "  make clean         - Clean cache files"
	@echo "  make docker-up     - Start PostgreSQL & Redis"
	@echo "  make docker-down   - Stop containers"
	@echo "  make docker-logs   - View container logs"
	@echo "  make run           - Run the application"
	@echo "  make migrate       - Run Alembic migrations"

install:
	uv sync

dev:
	uv sync --extra dev

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check app/ tests/

format:
	uv run ruff format app/ tests/

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ app/__pycache__ app/**/__pycache__ tests/__pycache__

docker-up:
	docker compose up -d
	@echo "Waiting for services..."
	@sleep 3

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

run:
	uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

migrate:
	uv run alembic upgrade head
