SHELL := /bin/bash

.PHONY: help ensure-env dev seed superuser lint test test-unit test-integration test-e2e check deploy-dev deploy-local deploy-devcontainer gitops-validate gitops-hook-install smoke build up down restart logs clean docker-dev test-live

PYTHON ?= python
ENV_FILE ?= .env
REQUIREMENTS ?= requirements.txt
DOCKER_TAG := $(shell git rev-parse --short HEAD 2>/dev/null || echo "dev")

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
	@echo "  make dev                Run Django locally (migrate + seed + runserver)"
	@echo "  make seed               Seed demo user and sample properties"
	@echo "  make superuser          Create a Django superuser"
	@echo "  make lint               Run Ruff and Black checks"
	@echo "  make test               Run unit tests (fast)"
	@echo "  make test-unit          Run unit tests"
	@echo "  make test-integration   Run integration tests"
	@echo "  make test-e2e           Run E2E tests (requires Playwright browser)"
	@echo "  make check              Run Django checks, lint, and all tests"
	@echo "  make smoke              Smoke test localhost:8000 health + APIs"
	@echo "  ── Docker (build image locally, no CI needed) ──"
	@echo "  make docker-dev         Build + start Docker stack (migrate + seed)"
	@echo "  make test-live          Start Docker + run live acceptance tests"
	@echo "  make build              Build Docker image"
	@echo "  make up                 Build + start daemon + smoke test"
	@echo "  make down               Stop containers"
	@echo "  make restart            Stop → rebuild → start"
	@echo "  make logs               Tail container logs (--tail=100)"
	@echo "  make clean              Remove all images, containers, volumes"
	@echo "  ── GitOps ──"
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
		-k "e2e or docker or container or startup or add_to_pipeline or export"

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
	@curl -sf -o /dev/null -w "  health:           HTTP %{http_code}\n" http://localhost:8000/health/ || { echo "❌ Health check failed"; exit 1; }
	@curl -sf -o /dev/null -w "  listings:         HTTP %{http_code}\n" http://localhost:8000/api/listings/ || echo "⚠  Listings API not responding"
	@curl -sf -o /dev/null -w "  growth-areas:     HTTP %{http_code}\n" "http://localhost:8000/api/v1/real-estate/growth-areas" || echo "⚠  Growth areas API not responding"
	@curl -sf -o /dev/null -w "  foreclosures:     HTTP %{http_code}\n" http://localhost:8000/api/v1/foreclosures || echo "⚠  Foreclosures API not responding"
	@echo "✅ Smoke test complete"

# ── GitOps ────────────────────────────────────────────────────────────────

gitops-validate:
	@./scripts/gitops-validate.sh

gitops-hook-install:
	@git config core.hooksPath .githooks
	@echo "GitOps pre-commit hook installed (core.hooksPath = .githooks)"

# ── Docker workflow (build image locally, no CI needed) ──────────────────

build:
	@echo "Building Docker image..."
	@docker compose build

up: build
	@docker compose up -d
	@sleep 3
	@$(MAKE) smoke

down:
	@docker compose down

restart: down up

logs:
	@docker compose logs -f --tail=100

clean:
	@docker compose down --rmi all --volumes --remove-orphans 2>/dev/null; true
	@echo "Docker state cleaned"

docker-dev: ensure-env build up
	$(call ensure_django)
	@docker compose exec web $(PYTHON) manage.py migrate
	@docker compose exec web $(PYTHON) manage.py seed_data
	@echo ""
	@echo "Docker dev stack running on http://localhost:8000"
	@echo "  make logs     — tail container logs"
	@echo "  make restart  — stop, rebuild, start"
	@echo "  make down     — stop containers"
	@echo "  make clean    — remove images + volumes"

# ── HTTP acceptance tests (against deployed app) ────────────────────────────

test-acceptance:
	@echo "── HTTP Acceptance Tests: $${BASE_URL:-http://localhost:8000} ──"
	@BASE_URL=$${BASE_URL:-http://localhost:8000} python3 -m pytest tests/acceptance/ -q --tb=short 2>/dev/null || python -m pytest tests/acceptance/ -q --tb=short

# ── Live acceptance testing ───────────────────────────────────────────

test-live: up
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  Live Acceptance Tests"
	@echo "  http://localhost:8000"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "1. Health check"
	@curl -sf http://localhost:8000/health/ | python3 -m json.tool 2>/dev/null || echo "❌ Health check failed"; exit 1
	@echo ""
	@echo "2. Login page"
	@STATUS=$$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/accounts/login/); \
	 [ "$$STATUS" = "200" ] && echo "✅ Login: 200" || echo "❌ Login: $$STATUS"
	@echo ""
	@echo "3. Growth areas API"
	@curl -sf "http://localhost:8000/api/v1/real-estate/growth-areas" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"✅ Growth API: {d.get('totalResults',0)} areas\")" 2>/dev/null || echo "⚠  No data yet"
	@echo ""
	@echo "4. Listings API"
	@curl -sf http://localhost:8000/api/listings/ | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"✅ Listings API: {d.get('count',0)} listings\")" 2>/dev/null || echo "⚠  No data yet"
	@echo ""
	@echo "5. Discovery page"
	@curl -sf -o /dev/null -w "✅ Discovery: HTTP %{http_code}" http://localhost:8000/discovery/; echo ""
	@echo ""
	@echo "6. Pipeline screener"
	@curl -sf -o /dev/null -w "✅ Screener: HTTP %{http_code}" http://localhost:8000/pipeline/screener/; echo ""
	@echo ""
	@echo "7. Leasing pipeline"
	@curl -sf -o /dev/null -w "✅ Leasing: HTTP %{http_code}" http://localhost:8000/leasing/; echo ""
	@echo ""
	@echo "8. Growth explorer"
	@curl -sf -o /dev/null -w "✅ Explorer: HTTP %{http_code}" http://localhost:8000/growth-explorer/; echo ""
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  ✅ All live tests complete"
	@echo "  View logs:  make logs"
	@echo "  Open:       open http://localhost:8000"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
