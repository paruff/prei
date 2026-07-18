# Specification: GitOps Phase 1 — Deployment Manifests
# Written: 2026-07-18
# Status: Draft for feature-flow implementation

---

## 0. Executive Summary

Create the `deploy/` directory with docker-compose manifests and wire the
`gitops-deploy` CI job to automatically update image tags on every successful
build. This is Phase 1 of the GitOps compliance roadmap — prerequisite for
uFawkesObs integration.

---

## 1. Problem Statement

**Current state:** No deployment manifests in git. The `gitops-deploy` job in
`docker-publish.yml` assumes a separate GitOps repo with kustomization.yaml
that doesn't exist. Image tags are not tracked as declarative state.

**Desired state:**
- `deploy/base/docker-compose.yml` — declarative service definition
- `deploy/overlays/production/docker-compose.override.yml` — production overrides
- CI automatically writes the image digest to the production manifest on build
- `GITOPS_REPO` variable points to this repo (self-hosted manifest)

---

## 2. Requirements

| ID | Description | Priority |
|---|---|---|
| F-01 | `deploy/base/docker-compose.yml` defines the service (port 8000, env vars, volumes) | P0 |
| F-02 | `deploy/overlays/production/docker-compose.override.yml` overrides image tag and secrets | P0 |
| F-03 | `docker-publish.yml` gitops-deploy job writes image digest to production overlay | P0 |
| F-04 | `GITOPS_REPO` defaults to this repo when set to self-reference or empty | P1 |
| F-05 | `scripts/gitops-validate.sh` includes `deploy/` manifests in validation | P1 |

---

## 3. Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-01 | `deploy/base/docker-compose.yml` exists with service definition | unit |
| AC-02 | `deploy/overlays/production/docker-compose.override.yml` exists with image tag placeholder | unit |
| AC-03 | gitops-validate.sh runs successfully against deploy/ manifests | unit |
| AC-04 | docker-publish.yml references `deploy/overlays/production/docker-compose.override.yml` | unit |
| AC-05 | Manifest files are valid docker-compose YAML | unit |
