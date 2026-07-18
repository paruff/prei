# GitOps Compliance Audit — prei

> Audit date: 2026-07-18
> Reference: AGENTS.md GitOps Principles (1-9)
> Target: uFawkesObs integration readiness

---

## Summary

| Principle | Status | Evidence |
|---|---|---|
| 1 — Git is source of truth | ✅ Compliant | 9 workflows, Dockerfile, compose, scripts all in git |
| 2 — Immutable artifacts | ✅ Compliant | 9 `@sha256` image digest references in workflows |
| 3 — PR gates = deploy gates | ✅ Compliant | `ci-quality.yml` + `main-ci-guard.yml` block broken deploys |
| 4 — Declarative pipelines | ✅ Compliant | All workflows declare desired state, not imperative scripts |
| 5 — Artifact verification | ✅ Compliant | `post-deployment.yml` smoke + acceptance + security + rollback |
| 6 — Rollback = git revert | ✅ Compliant | `post-deployment.yml` rollback job uses `git revert` on GitOps repo |
| 7 — Observability built-in | ✅ Compliant | 62 `job-start`/`job-finish` timestamps across all workflows |
| 8 — Progressive delivery | 🟡 Plan only | `docs/DEPLOYMENT_STRATEGY.md` exists; deferred until K8s |
| 9 — Naming is infrastructure | ✅ Compliant | Conventional Commits enforced via CI regex |

---

## Gap Analysis

### 1. Deployment Manifest (GITOPS_REPO)

**Current:** No `overlays/`, `kustomization.yaml`, or K8s manifests. Single-instance Docker deploy (Render/Docker compose).

**uFawkesObs Requirement:** uFawkesObs reads GitOps manifests from a configured `GITOPS_REPO`. Without manifests, it cannot reconcile or observe the deployment state.

**Action:**
- Create `deploy/` directory with docker-compose-based manifests
- Add `overlays/production/docker-compose.override.yml` with production overrides
- Set `GITOPS_REPO` variable to point to this repo or a separate manifest repo
- Update `docker-publish.yml` gitops-deploy job to write image tags to these manifests

### 2. uFawkesObs Integration

**Current:** No uFawkesObs references anywhere in the codebase.

**Action:**
- Add uFawkesObs webhook target to `post-deployment.yml`
- Configure uFawkesObs to scrape `docker-publish.yml` and `post-deployment.yml` run history
- Export DORA metrics: deploy frequency, lead time, change failure rate, MTTR
- Add `docs/UFAWKES_OBS_SETUP.md` with integration guide

### 3. Artifact Provenance

**Current:** `docker-publish.yml` has an `attest` job that generates build provenance. Good.

**uFawkesObs Requirement:** Verification that deployed images match attested digests.

**Action:**
- Ensure uFawkesObs can verify `attest-build-provenance` output
- Add image signature verification to `post-deployment.yml`

### 4. Namespace Separation

**Current:** No namespace/separation between CI, staging, and production workflows. Everything runs in one GitHub repository with no environment isolation.

**Action:**
- Add GitHub Environments (CI, staging, production) with protection rules
- Require approval for production deployments
- Tag deployments with environment metadata

---

## Compliance Roadmap

### Phase 1: Manifest Deployment (next week)

| Task | Effort |
|---|---|
| Create `deploy/` directory with base docker-compose manifest | 1 commit |
| Add `overlays/production/` with production overrides | 1 commit |
| Update `docker-publish.yml` to write image tags to manifests | 2 commits |
| Configure `GITOPS_REPO` variable in GitHub | 1 commit |

### Phase 2: uFawkesObs Integration (week after)

| Task | Effort |
|---|---|
| Deploy uFawkesObs to a uFawkes cluster | 1 day |
| Configure uFawkesObs to monitor this repo | 1 commit |
| Add webhook from uFawkesObs to `post-deployment.yml` | 1 commit |
| Validate DORA metrics are being collected | 1 day |
| Document setup in `docs/UFAWKES_OBS_SETUP.md` | 1 commit |

### Phase 3: Hardening ✅ (complete)

| Task | Status |
|---|---|
| Add GitHub Environments with approval gates | ✅ `environment: production` in publish job |
| Add image signature verification | ✅ `gh attestation verify` in `post-deployment.yml` |
| Add drift detection between git and deployed state | ✅ `scripts/drift-check.sh` + `make drift-check` |

---

## Current Score: 8/9 compliant

The remaining gap (progressive delivery/canary) is infra-dependent — it requires
K8s or a multi-replica deploy target. The architecture plan exists in
`docs/DEPLOYMENT_STRATEGY.md` and is ready when infrastructure supports it.
