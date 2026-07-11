SHELL := /bin/bash

.PHONY: help ensure-env dev seed superuser lint test test-unit test-integration test-e2e check deploy-dev deploy-local deploy-devcontainer gitops-validate gitops-hook-install smoke

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
	@echo "  make dev                Run migrate + seed_data and start the Django dev server"
	@echo "  make seed               Seed demo user and sample properties"
	@echo "  make superuser          Create a Django superuser"
	@echo "  make lint               Run Ruff and Black checks"
	@echo "  make test               Run unit tests (fast)"
	@echo "  make test-unit          Run unit tests"
	@echo "  make test-integration   Run integration tests"
	@echo "  make test-e2e           Run E2E tests (requires Playwright browser)"
	@echo "  make check              Run Django checks, lint, and all tests"
	@echo "  make deploy-dev         Start Docker stack on Docker host"
	@echo "  make deploy-local       Start Django locally + smoke test"
	@echo "  make deploy-devcontainer Start devcontainer + smoke test"
	@echo "  make smoke              Smoke test against http://localhost:8000"
	@echo "  make gitops-validate    Run GitOps best-practice validation"
	@echo "  make gitops-hook-install Install GitOps pre-commit hook"

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

# ── Tests by layer ────────────────────────────────────────────────────────

test: test-unit

test-unit:
	$(call ensure_django)
	@DJANGO_SETTINGS_MODULE=investor_app.settings_test $(PYTHON) -m pytest tests/ core/tests/ tests_bdd/ \
		-q --tb=short \
		-k "not e2e and not docker and not integration and not container and not startup and not add_to_pipeline and not export"

test-integration:
	$(call ensure_django)
	@echo "Running integration tests..."
	@DJANGO_SETTINGS_MODULE=investor_app.settings_test $(PYTHON) -m pytest tests/ core/tests/ \
		-v --tb=short \
		-k "integration"

test-e2e:
	$(call ensure_django)
	@echo "Running E2E tests (requires Playwright browser)..."
	@DJANGO_SETTINGS_MODULE=investor_app.settings_test $(PYTHON) -m pytest tests/ \
		-v --tb=short \
		-k "e2e or docker or container or startup or add_to_pipeline"

check: ensure-env
	$(call ensure_django)
	@$(PYTHON) manage.py check
	@$(MAKE) lint
	@$(MAKE) test-unit
	@$(MAKE) test-integration
	@$(MAKE) test-e2e

# ── Deploy ────────────────────────────────────────────────────────────────

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

deploy-local: ensure-env
	$(call ensure_django)
	@$(PYTHON) manage.py migrate --noinput
	@echo "Starting Django on http://localhost:8000 ..."
	@$(PYTHON) manage.py runserver 0.0.0.0:8000 &
	@sleep 3
	@$(MAKE) smoke
	@echo "Server running. Press Ctrl+C to stop."

deploy-devcontainer:
	@docker compose -f .devcontainer/docker-compose.yml up -d
	@sleep 5
	@echo "── Smoke test: devcontainer ──"
	@curl -sf -o /dev/null http://localhost:8000/health/ && echo "✅ Devcontainer healthy" || echo "⚠  Health check not responding (may need more startup time)"

# ── Post-deploy smoke ─────────────────────────────────────────────────────

smoke:
	@echo "── Smoke test: http://localhost:8000 ──"
	@curl -sf -o /dev/null -w "  health:        HTTP %{http_code}\n" http://localhost:8000/health/ || { echo "❌ Health check failed"; exit 1; }
	@curl -sf -o /dev/null -w "  properties:    HTTP %{http_code}\n" http://localhost:8000/api/properties/ || echo "⚠  Properties API not responding"
	@curl -sf -o /dev/null -w "  growth-areas:  HTTP %{http_code}\n" http://localhost:8000/api/growth-areas/ || echo "⚠  Growth areas API not responding"
	@curl -sf -o /dev/null -w "  foreclosures:  HTTP %{http_code}\n" http://localhost:8000/api/foreclosures/ || echo "⚠  Foreclosures API not responding"
	@echo "✅ Smoke test complete"

# ── GitOps ────────────────────────────────────────────────────────────────

gitops-validate:
	@./scripts/gitops-validate.sh

gitops-hook-install:
	@git config core.hooksPath .githooks
	@echo "GitOps pre-commit hook installed (core.hooksPath = .githooks)"
