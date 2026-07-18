# Specification: GitOps Phase 2 — uFawkesObs Integration
# Written: 2026-07-18
# Status: Draft for feature-flow implementation

---

## 0. Executive Summary

Phase 2 documents the uFawkesObs integration and adds the webhook/configuration
needed for uFawkesObs to monitor this project's GitOps pipeline. When uFawkesObs
is deployed, it will collect DORA metrics: deploy frequency, lead time, change
failure rate, and mean time to recovery.

---

## 1. Problem Statement

**Current state:**
- No uFawkesObs integration documentation or configuration
- No webhook registered with uFawkesObs
- No DORA metrics collection pipeline
- `post-deployment.yml` doesn't notify uFawkesObs on deploy events

**Desired state:**
- `docs/UFAWKES_OBS_SETUP.md` — complete integration guide
- `post-deployment.yml` sends webhook to uFawkesObs on deploy success/failure
- DORA metrics collection script that uFawkesObs can consume
- Configuration variables documented for `GITOPS_REPO`, webhook URL, etc.

---

## 2. Requirements

| ID | Description | Priority |
|---|---|---|
| F-01 | UFAWKES_OBS_SETUP.md documents the complete integration flow | P0 |
| F-02 | post-deployment.yml posts deploy events to uFawkesObs webhook | P1 |
| F-03 | DORA metrics script outputs JSON that uFawkesObs can consume | P1 |
| F-04 | GitHub variables documented (UFAWKES_WEBHOOK_URL, GITOPS_REPO, etc.) | P0 |

---

## 3. Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-01 | docs/UFAWKES_OBS_SETUP.md exists with integration steps | unit |
| AC-02 | Document includes webhook registration instructions | unit |
| AC-03 | post-deployment.yml has a deploy-notify step that POSTs to uFawkesObs | unit |
| AC-04 | scripts/dora-metrics.sh outputs JSON with deploy_frequency, lead_time, change_failure_rate, mttr | unit |
