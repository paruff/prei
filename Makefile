SHELL := /bin/bash

.PHONY: help ensure-env dev seed superuser lint test check deploy-dev gitops-validate gitops-hook-install

PYTHON ?= python
ENV_FILE ?= .env
REQUIREMENTS ?= requirements.txt

# Check Django is installed; install deps if not (handles recovery containers
# or incomplete devcontainer postCreateCommand).
define ensure_django
	@$(PYTHON) -c "import django" 2>/dev/null || { \
		echo "Django not found — installing dependencies..."; \
		$(PYTHON) -m pip install --upgrade pip==26.1.2 setuptools==83.0.0 wheel==0.46.2 && \
		$(PYTHON) -m pip install -r $(REQUIREMENTS); \
	}
endef

help:
	@echo "Available targets:"
	@echo "  make dev              Run migrate + seed_data and start the Django dev server"
	@echo "  make seed             Seed demo user and sample properties"
	@echo "  make superuser        Create a Django superuser"
	@echo "  make lint             Run Ruff and Black checks"
	@echo "  make test             Run the test suite"
	@echo "  make check            Run Django checks, lint, and tests"
	@echo "  make deploy-dev       Start Docker stack on Docker host"
	@echo "  make gitops-validate  Run GitOps best-practice validation"
	@echo "  make gitops-hook-install  Install GitOps pre-commit hook"

ensure-env:
	@if [[ ! -f $(ENV_FILE) ]]; then \
		cp .env.example $(ENV_FILE); \
		echo "Created $(ENV_FILE) from .env.example"; \
	fi

dev: ensure-env
	$(call ensure_django)
	@$(PYTHON) manage.py migrate
	@$(PYTHON) manage.py seed_data
	@$(PYTHON) manage.py runserver 0.0.0.0:8000

seed: ensure-env
	$(call ensure_django)
	@$(PYTHON) manage.py seed_data

superuser: ensure-env
	$(call ensure_django)
	@$(PYTHON) manage.py createsuperuser

lint:
	@ruff check .
	@ruff format --check .

test: ensure-env
	$(call ensure_django)
	@$(PYTHON) -m pytest -q

check: ensure-env
	$(call ensure_django)
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
	@docker compose exec web $(PYTHON) manage.py seed_data
	@echo "Docker stack is running on port 8000"

gitops-validate:
	@./scripts/gitops-validate.sh

gitops-hook-install:
	@git config core.hooksPath .githooks
	@echo "GitOps pre-commit hook installed (core.hooksPath = .githooks)"
