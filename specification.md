# Specification: Phase C — Deployment Reliability
# Written: 2026-07-18
# Status: Draft for feature-flow implementation

---

## 0. Executive Summary

Phase C makes deployment safe and measurable. Not through canary infrastructure
(which requires K8s/replicas this project doesn't have), but through the three
controls available today: automated security scanning, flaky test elimination,
and reliability metrics.

C-1 (canary) is documented as an architectural plan, not implemented.

---

## 1. Problem Statement

**Current state:**
- OWASP ZAP runs in passive baseline mode only — no active scanning for injection/XSS
- Flaky tests are not detected or quarantined — "rerun CI" culture wastes time
- No SLOs defined — no way to measure deployment reliability
- No canary deployment capability — deploy means "ship to 100% and pray"

**Desired state:**
- OWASP ZAP full active scan against staging with authentication support
- pytest-retry plugin detects and retries flaky tests; quarantines after N failures
- SLO dashboard: deployment frequency, change failure rate, mean time to recovery
- Canary deployment plan documented for future infra

---

## 2. Scope

### Implement

| Task | Description |
|---|---|
| C-2 | Full OWASP ZAP active scan (auth-aware, spider, XSS/injection rules) |
| C-3 | SLO foundation: deploy frequency + failure rate tracked in CI |
| C-4 | Flaky test retry + quarantine mechanism via pytest-rerunfailures |

### Document (not implement)

| Task | Description |
|---|---|
| C-1 | Canary deployment architecture plan — reference for future K8s migration |

---

## 3. Requirements

| ID | Description | Priority |
|---|---|---|
| F-01 | OWASP ZAP full scan runs against staging URL with auth context | P0 |
| F-02 | Active scan includes XSS, SQL injection, CSRF, auth bypass rules | P0 |
| F-03 | Flaky test detection: retry once, quarantine after 3 flakes | P1 |
| F-04 | SLO metrics: deployment frequency (last 30 days), change failure rate (%) | P1 |
| F-05 | SLO metrics computed from CI run history and reported in PR description | P1 |
| F-06 | Canary deployment plan documented in docs/DEPLOYMENT_STRATEGY.md | P2 |

---

## 4. Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-01 | `post-deployment.yml` security job uses full ZAP scan with `-a` (active) flag | unit |
| AC-02 | ZAP scan configuration includes auth context (session token or credentials) | unit |
| AC-03 | CI quality gate includes `--reruns 1 --reruns-delay 5` on unit tests | unit |
| AC-04 | A test that fails twice is marked as flaky with `@pytest.mark.flaky` | unit |
| AC-05 | SLO report is generated from CI run data and attached to build summary | unit |
| AC-06 | `make test-slos` computes deploy frequency and failure rate from git log | unit |
| AC-07 | `docs/DEPLOYMENT_STRATEGY.md` exists with canary architecture plan | unit |
