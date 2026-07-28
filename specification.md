# Specification: Phase C (partial) — Deployment Reliability (docs/TOP_01_PLAN.md)
# Written: 2026-07-28
# Status: IN PROGRESS (feat/top01-phase-c)

---

## 0. Problem

`docs/TOP_01_PLAN.md` Phase C ("Deployment Reliability") lists four gaps:
canary deployment (C-1), an authenticated OWASP ZAP full scan (C-2), an SLO
dashboard (C-3), and flaky-test quarantine + a flaky-test dashboard (C-4).

C-1 and C-3 both need infrastructure this repo doesn't have — a load
balancer/traffic-splitting layer for canary, and a monitoring/metrics stack
for SLOs — which `docs/TOP_01_PLAN.md`'s own "What You Can't Ship Yet"
section already flags. They are deferred to a future phase, not silently
dropped; see `docs/TOP_01_PLAN.md` and `docs/KNOWN_LIMITATIONS.md` LIMIT-22
for the scope decision. **This PR implements C-2 and C-4 only.**

Prior state:
- `post-deployment.yml`'s `security` job already runs an unauthenticated full
  ZAP scan (`zaproxy/action-full-scan@v1`, `cmd_options: "-a"`) against the
  live deployed URL. ZAP never sees anything behind `/accounts/login/`.
- `pytest-rerunfailures` was already wired via `pytest.ini`'s
  `--reruns 1 --reruns-delay 5` — a rerun happens, but nothing records which
  tests needed it, and nothing quarantines a test that fails repeatedly.

## 1. Requirements

- C-2: An OWASP ZAP full scan authenticates before spidering/scanning, so it
  can reach pages behind Django's login-required views.
- C-4: A test that needed a rerun to pass is recorded; once a given test's
  cumulative flaky count crosses a threshold, it's quarantined (kept running
  and reporting, but never fails the build) until fixed.

## 2. Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-C2-01 | `core/management/commands/seed_zap_scan_user.py` idempotently creates/updates a non-staff, non-superuser scan account from `ZAP_AUTH_USERNAME`/`ZAP_AUTH_PASSWORD` env vars | unit |
| AC-C2-02 | `.zap/prei-auth-context.xml` defines form-based auth against `/accounts/login/` with logged-in/out indicator regexes | manual |
| AC-C2-03 | `ci-quality.yml`'s `zap-authenticated-scan` job seeds the account, boots an ephemeral `runserver` instance against a fresh migrated SQLite DB, and runs `zap-full-scan.py` with the auth context | ci |
| AC-C2-04 | `zap-authenticated-scan` is a required check in `pr-gates-pass` | ci |
| AC-C2-05 | `docs/KNOWN_LIMITATIONS.md` documents that the authenticated scan targets an ephemeral CI instance, not the live deployment | manual |
| AC-C4-01 | `pytest.ini`'s `addopts` includes `--report-log=.pytest-report.jsonl` | unit |
| AC-C4-02 | `.github/scripts/flaky_report.py --mode report` detects a rerun-then-pass nodeid from a report-log file and prints a markdown summary without touching the ledger | unit |
| AC-C4-03 | `.github/scripts/flaky_report.py --mode write` increments `docs/quality/flaky_tests.json`'s per-nodeid count and marks it quarantined once the count reaches the threshold (default 3), writing matching nodeids to `tests/.flaky_quarantine.txt` | unit |
| AC-C4-04 | Root `conftest.py`'s `pytest_collection_modifyitems` hook marks nodeids listed in `tests/.flaky_quarantine.txt` as `xfail(strict=False)` so they can't fail the build | unit |
| AC-C4-05 | `ci-quality.yml`'s `tests-unit`/`tests-integration`/`tests-e2e` jobs run `flaky_report.py --mode report` and upload the report log as an artifact | ci |
| AC-C4-06 | `docker-publish.yml`'s `live-test` job (push-to-`main` only) runs `flaky_report.py --mode write` and bot-commits any ledger/quarantine change back to `main` | ci |

## 3. Out of Scope (this PR)

- C-1 (canary deployment) — deferred, needs traffic-splitting infra.
- C-3 (SLO dashboard) — deferred, needs a monitoring/metrics stack.
- Authenticating the ZAP scan against the real deployed environment — would
  need provisioning a scan account and secrets on live infra, the same
  category of gap as C-1/C-3.
