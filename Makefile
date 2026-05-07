SHELL := /bin/bash

.PHONY: help ensure-env dev superuser lint test check deploy-dev

PYTHON ?= python
ENV_FILE ?= .env

help:
	@echo "Available targets:"
	@echo "  make dev         Run migrations and start the Django dev server in Codespaces/devcontainer"
	@echo "  make superuser   Create a Django superuser in the current environment"
	@echo "  make lint        Run Ruff and Black checks"
	@echo "  make test        Run the test suite"
	@echo "  make check       Run Django checks, lint, and tests"
	@echo "  make deploy-dev  Start the image-based Docker stack on a Docker host"

ensure-env:
	@if [[ ! -f $(ENV_FILE) ]]; then \
		cp .env.example $(ENV_FILE); \
		echo "Created $(ENV_FILE) from .env.example"; \
	fi

dev: ensure-env
	@$(PYTHON) manage.py migrate
	@$(PYTHON) manage.py runserver 0.0.0.0:8000

superuser: ensure-env
	@$(PYTHON) manage.py createsuperuser

lint:
	@ruff check .
	@black --check .

test: ensure-env
	@$(PYTHON) -m pytest -q

check: ensure-env
	@$(PYTHON) manage.py check
	@$(MAKE) lint
	@$(MAKE) test

deploy-dev: ensure-env
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "Docker CLI is not available in this environment."; \
		echo "For rapid Codespaces development, use: make dev"; \
		echo "For image-based deployment, rebuild the devcontainer after enabling Docker or run this target on a Docker host."; \
		exit 1; \
	fi
	@docker compose up -d
	@docker compose exec web $(PYTHON) manage.py migrate
	@echo "Docker stack is running on port 8000"
