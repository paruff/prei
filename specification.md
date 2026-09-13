# Specification: Data Layer & Infrastructure Upgrades for Beta Readiness

**Feature**: Core product upgrades addressing top-0.1% feedback
**Status**: Draft
**Related**: M2 milestones (Beta Readiness)

---

## User Intent

A pro investor needs: (1) rent estimates for every property source to enable yield/PTR screening, (2) validated GACS weights backed by backtesting, (3) real crime data not dummies, (4) async background tasks so screening doesn't block, (5) shared pipeline with partners, (6) Postgres for production parity.

---

## Current State Assessment

| Gap | Current | Blocker |
|---|---|---|
| **Rent data** | VRM only has rent; HUD/USDA/ATTOM/County skip yield/PTR | Rentcast key missing; ATTOM rent fields untested |
| **GACS validation** | Experimental weights, no backtest | County→state employment fallback, school quality unwired, supply constraint hardcoded |
| **Crime data** | State dummies (TX=2.5, CA=3.5, other=3.0) | FBI CDE SPIKE failed; no viable path found |
| **Background tasks** | Sync re-screen on criteria change; VRM scrape in thread | No Celery; Gunicorn 30s timeout |
| **Multi-user** | PipelineProperty FK to User only | No team model, no sharing |
| **Database** | SQLite dev, Postgres prod (not parity) | LIMIT-05 |
| **CSP/Headers** | 8 ZAP WARN findings remain | LIMIT-23 |

---

## Requirements

### Functional Requirements

| ID | Requirement | Priority | Description |
|---|---|---|---|
| FR-1 | **Rentcast Integration** | Critical | Add Rentcast adapter; wire into screening rent fallback chain (VRM → Rentcast → HUD FMR) |
| FR-2 | **ATTOM Rent Fields** | High | Test if ATTOM Property API returns rent estimates; if yes, add as fallback |
| FR-3 | **GACS Backtest & Validation** | Critical | Backtest GACS composite against FHFA/Zillow historical appreciation; publish weight sensitivity; expose "confidence bands" |
| FR-4 | **GACS Signal Completion** | High | Wire school quality (GreatSchools); compute supply constraint from permit data; fix employment fallback to use county QCEW where available |
| FR-5 | **Real Crime Data** | High | Retry FBI CDE with correct endpoint/params; if blocked, evaluate SpotCrime/CityProtect/local PD APIs |
| FR-6 | **Postgres Migration** | Critical | Local dev via docker-compose; remove SQLite LIMIT-05; parity with prod |
| FR-7 | **Celery + Redis** | Critical | Async screening re-runs, VRM scrape, discovery; remove Gunicorn thread hacks |
| FR-8 | **Team/Shared Pipeline** | High | Team model; PipelineProperty FK to Team; shared visibility (owner/member/viewer) |
| FR-9 | **CSP & Security Headers** | High | Add django-csp middleware; CSP, Permissions-Policy, Cross-Origin-Resource-Policy; SRI on external scripts |

### Non-Functional Requirements

| ID | Requirement | Priority | Description |
|---|---|---|---|
| NFR-1 | **Rent coverage ≥ 90%** | Critical | Post-integration, ≥90% of discovered properties have rent estimate for screening |
| NFR-2 | **GACS predictive validity** | Critical | Backtest R² ≥ 0.4 vs 12-month price appreciation; publish methodology |
| NFR-3 | **Crime data granularity** | High | ZIP or census-tract level, not state-level |
| NFR-4 | **Async task latency < 5s** | High | Screening re-run, discovery completions under 5s user-visible |
| NFR-5 | **Team invite flow** | Medium | Invite by email; role-based access (owner/member/viewer) |
| NFR-6 | **Zero-downtime deploy** | Medium | Postgres + Celery supports blue/green or canary |

---

## Acceptance Criteria

| ID | Criterion | Test Type | Reasoning |
|---|---|---|---|
| AC-1 | Rentcast adapter returns rent for test ZIPs | live-system | Verify API contract |
| AC-2 | Screening runs yield/PTR for HUD property via Rentcast fallback | live-system | End-to-end blind spot fixed |
| AC-3 | GACS backtest report published (methodology + R²) | unit (file exists) | Validated weights |
| AC-4 | Crime adapter returns real data for test ZIP | live-system | No more dummies |
| AC-5 | `docker-compose up` brings up Postgres + Redis + app | live-system | Dev parity |
| AC-6 | Celery worker processes screening re-run async | live-system | No HTTP block |
| AC-7 | User can invite teammate to view pipeline | live-system | Shared pipeline works |
| AC-8 | CSP header present on all responses | live-system | ZAP WARN reduced |
| AC-9 | SRI attributes on all external scripts | unit | ZAP 90003 resolved |

---

## Constraints

1. **Decimal money** — all rent/currency stays Decimal
2. **Service-layer boundaries** — new adapters in `core/integrations/sources/`
3. **No Bootstrap** — custom design system only
4. **GitOps** — Docker image is artifact; manifests in git
5. **Spike first** — Rentcast and Crime API need feasibility before commit

---

## Out of Scope

- Mobile app / PWA enhancements
- MLS/RESO integration
- Tax strategy module
- 1031 exchange tracking
- Lender/agent deal sharing

---

## Governance Alignment

- **CHANGE_IMPACT_MAP.md** — update for new models (Team, Celery config), services (rent adapters, crime adapter)
- **KNOWN_LIMITATIONS.md** — resolve LIMIT-03, LIMIT-05, LIMIT-08, LIMIT-11, LIMIT-15, LIMIT-16, LIMIT-23
- **DEPLOYMENT_STRATEGY.md** — Postgres + Celery enables canary
