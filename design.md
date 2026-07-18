# Design: GitOps Phase 1 — Deployment Manifests
# Written: 2026-07-18
# Status: Draft

---

## 1. Directory Structure

```
deploy/
├── base/
│   └── docker-compose.yml          # Service definition (port, env, health)
└── overlays/
    └── production/
        └── docker-compose.override.yml  # Image tag, secrets, scale
```

---

## 2. Manifest Design

### 2.1 Base (`deploy/base/docker-compose.yml`)

```yaml
services:
  web:
    image: ghcr.io/paruff/prei:latest
    ports:
      - "8000:8000"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - DJANGO_ENV=production
      - DEBUG=False
      - RUN_MIGRATIONS=1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    restart: unless-stopped
```

### 2.2 Production Overlay (`deploy/overlays/production/docker-compose.override.yml`)

```yaml
services:
  web:
    image: ghcr.io/paruff/prei@sha256:PLACEHOLDER  # updated by CI
    restart: always
```

The CI job replaces `sha256:PLACEHOLDER` with the actual digest on every build.

---

## 3. CI Changes

### 3.1 Update `docker-publish.yml` gitops-deploy job

Change `GITOPS_MANIFEST_PATH` default from `overlays/production/kustomization.yaml` to `deploy/overlays/production/docker-compose.override.yml`.

The job already:
1. Checkouts the GitOps repo
2. Updates the manifest with `sed`
3. Commits and pushes

These mechanics don't change — only the default path.

### 3.2 Update `scripts/gitops-validate.sh`

Add `deploy/**/*.yml` to the list of validated files so pre-commit and CI check manifest validity.

---

## 4. File Changes

| File | Change | Purpose |
|---|---|---|
| `deploy/base/docker-compose.yml` | New | Base service definition |
| `deploy/overlays/production/docker-compose.override.yml` | New | Production overlay |
| `.github/workflows/docker-publish.yml` | Modified | Update default GITOPS_MANIFEST_PATH |
| `scripts/gitops-validate.sh` | Modified | Include deploy/ in validation |