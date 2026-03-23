PYTHON ?= uv run
DOCKER_COMPOSE ?= docker compose

.PHONY: up down restart logs migrate migrate-down revision run test lint build

up:
	$(DOCKER_COMPOSE) up -d --build

build:
	$(DOCKER_COMPOSE) build

down:
	$(DOCKER_COMPOSE) down

restart: down up

logs:
	$(DOCKER_COMPOSE) logs -f

migrate:
	$(PYTHON) alembic upgrade head

migrate-down:
	$(PYTHON) alembic downgrade -1

revision:
	$(PYTHON) alembic revision --autogenerate -m "$(m)"

run:
	$(PYTHON) uvicorn main:app --reload

test:
	$(PYTHON) pytest -q

lint:
	$(PYTHON) python -m compileall app tests main.py
