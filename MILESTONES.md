# MILESTONES.md (months) — prei

**Horizon**: 3–6 months | **Owner**: Product lead (Phil) | **Review**: Monthly

---

## Horizon Map

| Horizon | Months | Focus |
|---------|--------|-------|
| **H1** (now) | 1–2 | Alpha stabilization: documentation, known limitations, CI/CD gates |
| **H2** (next) | 3–4 | Beta readiness: Postgres, auth, production deployment |
| **H3** (future) | 5–6 | Growth: portfolio tracking, leasing pipeline, multi-user |

---

## H1 — Alpha Stabilization (Months 1–2)

| Milestone | Deliverables | Status | Issues |
|---|---|---|---|
| **M1.1** Investor Workflow Documentation | 4 how-to guides (Growth Areas, Discovery, Screening, Underwriting), workflow overview, UI patterns reference | In progress | #335 |
| **M1.2** Finance Utils Consolidation | Single-source KPI functions, eliminate duplicate `score_listing_v2` | Done | finance-utils-split PR |
| **M1.3** CI Quality Gates | OWASP ZAP authenticated scan, production settings tests | Done | LIMIT-22 |
| **M1.4** GACS Growth Data | `populate_growth_areas` command, rent growth rate populated | Done | GACS-FMR-1 (PR #278) |
| **M1.5** Known Limitations Triage | All active limitations documented, prioritized, workarounds noted | Done | LIMIT-01 through LIMIT-23 |

---

## H2 — Beta Readiness (Months 3–4)

| Milestone | Deliverables | Status | Issues |
|---|---|---|---|
| **M2.1** Postgres Migration | Production database, remove LIMIT-05, test parity | Planned | — |
| **M2.2** Auth Hardening | Session cookies HttpOnly/Secure, CSP headers, SRI attributes | Planned | LIMIT-23 |
| **M2.3** Sanitized Logging | `sanitized_exc_info` helper, restore tracebacks without PII | Planned | LIMIT-03, LIMIT-09 |
| **M2.4** Growth Area Consistency | Resolve HTML vs API divergence in GrowthArea vs MarketSnapshot | Planned | LIMIT-08 |
| **M2.5** Rent Data Coverage | Rentcast adapter or equivalent to enable yield screening for all source types | Planned | LIMIT-11 |

---

## H3 — Growth Features (Months 5–6)

| Milestone | Deliverables | Status | Issues |
|---|---|---|---|
| **M3.1** Portfolio Analytics | Monthly actuals vs pro-forma, investment analysis, hold-period projections | Backlog | LIMIT-14 (partial) |
| **M3.2** Leasing Pipeline Completion | Listing → tenant screening → lease signing → rent collection tracking | Backlog | LIMIT-14 |
| **M3.3** Background Task Support | Celery integration for async screening re-runs | Backlog | LIMIT-15 |
| **M3.4** Multi-user Support | Team-based pipeline sharing, role-based access | Backlog | LIMIT-16 |

---

## Release Gates

Before any release ships, ALL of these must be true:

| Gate | What must be true | How verified |
|---|---|---|
| **Tests pass** | All unit + integration + BDD tests green | `make test` or CI |
| **Lint clean** | ruff, mypy, no warnings | `make lint` |
| **Docs updated** | Relevant docs match code behavior | Manual review + live-system verification |
| **CHANGELOG current** | New entries for all user-facing changes | CHANGELOG.md updated |
| **Git tag** | Semantic version tag pushed | `git tag vX.Y.Z` |
| **Deploy + verify** | Post-deployment smoke/acceptance/performance/security tests pass | CI pipeline |

---

## Traceability: Milestones → Vision Principles

| Milestone | Vision Principle |
|---|---|
| M1.1 (Documentation) | #6 (Investor-first UX), #7 (Data confidence) |
| M1.2 (Finance consolidation) | #1 (Decimal-first money), #2 (Service-layer boundaries) |
| M1.3 (CI gates) | #5 (GitOps deployment) |
| M1.4 (GACS data) | #8 (One system, full lifecycle) |
| M2.1 (Postgres) | #4 (SQLite dev / Postgres prod) |
| M2.2 (Auth hardening) | #8 (One system, full lifecycle — trust) |
| M2.4 (Growth area consistency) | #3 (No Bootstrap — custom design), #8 (One system) |
| M2.5 (Rent data) | #7 (Data confidence), #8 (Full lifecycle) |
| M3.1 (Portfolio) | #6 (Investor-first UX), #8 (Full lifecycle) |
| M3.2 (Leasing) | #8 (One system, full lifecycle) |

---

## How This Connects

| Doc | What it answers | Reference |
|---|---|---|
| `VISION.md` | What are we building and why? | ↗ links up |
| `EXECUTION_QUEUE.md` | What are we working on this week? | ↘ links down |
| `CHANGELOG.md` | What has shipped? | parallel |
