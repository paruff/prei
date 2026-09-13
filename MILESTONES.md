# MILESTONES.md (months) — prei

**Horizon**: 3–6 months | **Owner**: Product lead (Phil) | **Review**: Monthly

---

## Horizon Map

| Horizon | Months | Focus |
|---------|--------|-------|
| **H1** (now) | 1–2 | Alpha stabilization: documentation, known limitations, CI/CD gates |
| **H2** (next) | 2–4 | Beta readiness: rent data, GACS validation, crime, Postgres, Celery, multi-user |
| **H3** (future) | 4–6 | Growth: portfolio tracking, leasing pipeline, advanced analytics |

---

## H1 — Alpha Stabilization (Month 1–2) ✅ COMPLETE

| Milestone | Deliverables | Status | Issues |
|---|---|---|---|
| **M1.1** Investor Workflow Documentation | 4 how-to guides, workflow overview, UI patterns reference | **Done** | #335 (closed), PR #433 |
| **M1.2** Finance Utils Consolidation | Single-source KPI functions, eliminate duplicate `score_listing_v2` | **Done** | finance-utils-split PR |
| **M1.3** CI Quality Gates | OWASP ZAP authenticated scan, production settings tests | **Done** | LIMIT-22 resolved |
| **M1.4** GACS Growth Data | `populate_growth_areas` command, rent growth rate populated | **Done** | GACS-FMR-1 (PR #278) |
| **M1.5** Known Limitations Triage | All active limitations documented, prioritized, workarounds | **Done** | LIMIT-01 through LIMIT-23 |
| **M1.6** Security Headers (Phase 1) | `SESSION_COOKIE_HTTPONLY`, `SECURE_SERVER_HEADER`, middleware test | **Done** | LIMIT-23 partial (2/10 WARN) |

---

## H2 — Beta Readiness (Months 2–4)

### Phase H2A — Rent Data & GACS Validation (Month 2–3)

| Milestone | Deliverables | Status | Issues |
|---|---|---|---|
| **M2.1** Rentcast Spike | API key obtained, coverage test for TX/FL/TN, latency < 500ms | Planned | New issue |
| **M2.2** Rentcast Adapter + Fallback Chain | Adapter in `core/integrations/sources/`; screening uses VRM→Rentcast→ATTOM→HUD FMR | Planned | LIMIT-11 |
| **M2.3** ATTOM Rent Probe | Test ATTOM Property API for rent_estimate field; integrate if available | Planned | LIMIT-11 |
| **M2.4** GACS Backtest Script | `scripts/backtest_gacs.py`; grid search weights; R² ≥ 0.4 vs FHFA 12mo | Planned | LIMIT-02, LIMIT-17 |
| **M2.5** GACS Signal Completion | GreatSchools wired (schools); supply constraint from permits; employment fallback fix | Planned | LIMIT-02, LIMIT-17 |

### Phase H2B — Crime Data & Infrastructure (Month 3)

| Milestone | Deliverables | Status | Issues |
|---|---|---|---|
| **M2.6** Crime Adapter Retry + Fallback | FBI CDE retry with correct endpoint; if fail: SpotCrime/CityProtect eval | Planned | LIMIT-01 |
| **M2.7** Postgres + Redis (docker-compose) | Local dev parity; remove LIMIT-05; `docker-compose up` healthy | Planned | LIMIT-05 |
| **M2.8** Celery + Redis | Async screening re-run, discovery batch, VRM scrape; Gunicorn threads removed | Planned | LIMIT-15 |
| **M2.9** Team / Shared Pipeline | Team model, TeamMembership, PipelineProperty.team FK, invite flow (owner/member/viewer) | Planned | LIMIT-16 |

### Phase H2C — Security Hardening (Month 3–4)

| Milestone | Deliverables | Status | Issues |
|---|---|---|---|
| **M2.10** CSP & Security Headers | django-csp middleware; CSP, Permissions-Policy, CORP headers; SRI on externals | Planned | LIMIT-23 (8 WARN → 0) |
| **M2.11** ZAP Scan Clean Pass | Authenticated ZAP scan: 0 FAIL, 0 WARN | Planned | LIMIT-23 |

---

## H3 — Growth Features (Months 4–6)

| Milestone | Deliverables | Status | Issues |
|---|---|---|---|
| **M3.1** Portfolio Analytics | Monthly actuals vs pro-forma, investment analysis, hold-period projections | Backlog | LIMIT-14 (partial) |
| **M3.2** Leasing Pipeline Completion | Listing → tenant screening → lease signing → rent collection tracking | Backlog | LIMIT-14 |
| **M3.3** Advanced Market Intelligence | Rent trends, absorption rates, cap rate compression alerts | Backlog | — |
| **M3.4** API Surface for Partners | Read-only API for lenders/agents; deal sharing links | Backlog | — |

---

## Release Gates (per release)

| Gate | What must be true | How verified |
|---|---|---|
| **Tests pass** | All unit + integration + BDD tests green | `make test` or CI |
| **Lint clean** | ruff, mypy, no warnings | `make lint` |
| **Docs updated** | Relevant docs match code behavior | Manual review + live-system |
| **CHANGELOG current** | New entries for all user-facing changes | CHANGELOG.md updated |
| **Git tag** | Semantic version tag pushed | `git tag vX.Y.Z` |
| **Deploy + verify** | Post-deployment smoke/acceptance/performance/security | CI pipeline |
| **Rent coverage ≥ 90%** | Post-H2A, screening has rent for ≥90% properties | Live-system sampling |
| **GACS validated** | Backtest report published with R² | `scripts/backtest_gacs.py` output |

---

## Traceability: Milestones → Vision Principles

| Milestone | Vision Principle |
|---|---|
| M1.1 (Documentation) | #6 (Investor-first UX), #7 (Data confidence) |
| M1.2 (Finance consolidation) | #1 (Decimal-first money), #2 (Service-layer boundaries) |
| M1.3 (CI gates) | #5 (GitOps deployment) |
| M1.4 (GACS data) | #8 (One system, full lifecycle) |
| M2.1–M2.3 (Rent data) | #7 (Data confidence), #8 (Full lifecycle) |
| M2.4–M2.5 (GACS validation) | #6 (Investor-first UX), #7 (Data confidence), #8 (Full lifecycle) |
| M2.6 (Crime data) | #7 (Data confidence), #8 (Full lifecycle) |
| M2.7 (Postgres) | #4 (SQLite dev / Postgres prod) |
| M2.8 (Celery) | #2 (Service-layer boundaries), #8 (Full lifecycle) |
| M2.9 (Multi-user) | #8 (One system, full lifecycle — trust) |
| M2.10–M2.11 (Security) | #5 (GitOps), #8 (Full lifecycle — trust) |

---

## How This Connects

| Doc | What it answers | Reference |
|---|---|---|
| `VISION.md` | What are we building and why? | ↗ links up |
| `EXECUTION_QUEUE.md` | What are we working on this week? | ↘ links down |
| `CHANGELOG.md` | What has shipped? | parallel |
| `KNOWN_LIMITATIONS.md` | Which limitations each milestone resolves | parallel |
