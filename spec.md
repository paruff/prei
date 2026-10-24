# Specification: Data Layer & Infrastructure Upgrades for Beta Readiness

**Feature**: Core product upgrades addressing top-0.1% feedback
**Status**: Draft
**From**: [intent.md](intent.md) · **Plan**: [plan.md](plan.md) (Beta A/B/C)
**Decisions 2026-10-24**: single-user for now; SQLite for local runs, Postgres in production; Django 6.0. FR-6, FR-8, NFR-5, AC-5 and AC-7 removed; IDs are not reused.

---

## User Intent

See [intent.md](intent.md). In short: rent estimates for every property source, validated GACS weights, real crime data, screening that never blocks, and clean security headers.

---

## Current State Assessment

| Gap | Current | Blocker |
|---|---|---|
| **Rent data** | VRM only has rent; HUD/USDA/ATTOM/County skip yield/PTR | Rentcast key missing; ATTOM rent fields untested |
| **GACS validation** | Experimental weights, no backtest | County→state employment fallback, school quality unwired, supply constraint hardcoded |
| **Crime data** | State dummies (TX=2.5, CA=3.5, other=3.0) | FBI CDE SPIKE failed; no viable path found |
| **Background tasks** | Sync re-screen on criteria change; VRM scrape in thread | No Celery; Gunicorn 30s timeout |
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
| FR-7 | **Celery + Redis** | Critical | Async screening re-runs, VRM scrape, discovery; remove Gunicorn thread hacks (open: Celery vs lighter option, see intent.md open question 3) |
| FR-9 | **CSP & Security Headers** | High | Add django-csp middleware; CSP, Permissions-Policy, Cross-Origin-Resource-Policy; SRI on external scripts |

### Non-Functional Requirements

| ID | Requirement | Priority | Description |
|---|---|---|---|
| NFR-1 | **Rent coverage ≥ 90%** | Critical | Post-integration, ≥90% of discovered properties have rent estimate for screening |
| NFR-2 | **GACS predictive validity** | Critical | Backtest R² ≥ 0.4 vs 12-month price appreciation; publish methodology |
| NFR-3 | **Crime data granularity** | High | ZIP or census-tract level, not state-level |
| NFR-4 | **Async task latency < 5s** | High | Screening re-run, discovery completions under 5s user-visible |
| NFR-6 | **Zero-downtime deploy** | Medium | Postgres + Celery supports blue/green or canary (open: canary is a VISION non-goal; see intent.md open question 5) |

---

## Acceptance Criteria

| ID | Criterion | Test Type | Reasoning |
|---|---|---|---|
| AC-1 | Rentcast adapter returns rent for test ZIPs | live-system | Verify API contract |
| AC-2 | Screening runs yield/PTR for HUD property via Rentcast fallback | live-system | End-to-end blind spot fixed |
| AC-3 | GACS backtest report published (methodology + R²) | unit (file exists) | Validated weights |
| AC-4 | Crime adapter returns real data for test ZIP | live-system | No more dummies |
| AC-6 | Celery worker processes screening re-run async | live-system | No HTTP block |
| AC-8 | CSP header present on all responses | live-system | ZAP WARN reduced |
| AC-9 | SRI attributes on all external scripts | unit | ZAP 90003 resolved |

---

## Constraints

1. **Decimal money** — all rent/currency stays Decimal
2. **Service-layer boundaries** — new adapters in `core/integrations/sources/`
3. **No Bootstrap** — custom design system only
4. **GitOps** — Docker image is artifact; manifests in git
5. **Spike first** — Rentcast and Crime API need feasibility before commit
6. **Single-user** — no teams or sharing
7. **SQLite locally** — Postgres in production only

---

## Out of Scope

- Mobile app / PWA enhancements
- MLS/RESO integration
- Tax strategy module
- 1031 exchange tracking
- Lender/agent deal sharing
- Team/shared pipelines (single-user for now)
- Postgres for local development

---

## Governance Alignment

- **CHANGE_IMPACT_MAP.md** — update for Celery config and new services (rent adapters, crime adapter)
- **KNOWN_LIMITATIONS.md** — resolve LIMIT-03, LIMIT-08, LIMIT-11, LIMIT-15, LIMIT-23
- **DEPLOYMENT_STRATEGY.md** — Postgres + Celery enables canary
