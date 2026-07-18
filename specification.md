# Specification: GitOps Phase 3 — Hardening
# Written: 2026-07-18
# Status: Draft for feature-flow implementation

---

## 0. Executive Summary

Phase 3 adds the final GitOps hardening controls: GitHub deployment environments
with approval gates, image signature verification via Cosign, and drift detection
between the git state and the deployed runtime.

---

## 1. Problem Statement

**Current state:**
- No deployment environments defined — every push to main triggers a deploy
- No image signature verification — tampered images could reach production
- No drift detection — no automated check that deployed state matches git

**Desired state:**
- Production deployment requires approval via GitHub Environment
- Images published to GHCR are signed with Cosign keyless signing
- `post-deployment.yml` verifies image signature before smoke tests
- `scripts/drift-check.sh` detects and reports configuration drift

---

## 2. Requirements

| ID | Description | Priority |
|---|---|---|
| F-01 | GitHub Environment "production" created with required reviewers | P0 |
| F-02 | docker-publish.yml references the production environment | P1 |
| F-03 | Image attestation uses Cosign keyless signing (already present) | P0 |
| F-04 | post-deployment.yml verifies image signature before tests | P1 |
| F-05 | scripts/drift-check.sh compares deployed health against git manifests | P2 |

---

## 3. Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-01 | docker-publish.yml publish job references `environment: production` | unit |
| AC-02 | post-deployment.yml verifies image attestation via `gh attestation` | unit |
| AC-03 | scripts/drift-check.sh exists and compares git vs deployed state | unit |
| AC-04 | Workflow YAML is valid | unit |
