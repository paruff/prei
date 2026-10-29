# Specification: a functioning prei

**Status**: proposed (approved by merging the PR that changes this file)
**From**: [intent.md](intent.md) · **Plan**: [plan.md](plan.md) (goals G0–G3)
**Decisions**: 2026-10-24: single-user; SQLite local, Postgres for hosted; Django 6.0. 2026-10-29: Docker first, Render later; HUD FMR rent first, Rentcast after measurement.
**IDs**: FR-1 to FR-9 come from the superseded beta-readiness spec. FR-6, FR-8, NFR-5, AC-5 and AC-7 were removed. IDs are never reused.

---

## Current State Assessment

| Gap | Current | Blocker |
|---|---|---|
| **Runs anywhere** | Render not running; `docker compose up` needs the external `observability-lab` network | No local or hosted environment runs the journey |
| **Seed data** | `seed_markets`, `populate_growth_areas` run by hand | GACS empty after a fresh start (LIMIT-17) |
| **Journey proof** | Page and endpoint tests; kanban e2e | No test walks steps 1–9 |
| **Rent data** | Chain is VRM → stored estimate → Rentometer → HUD FMR (`_get_monthly_rent`) | Coverage never measured; LIMIT-11 may be stale |
| **Background tasks** | Re-screen on criteria change is synchronous | Only a blocker if it times out (LIMIT-15) |

---

## Requirements

`Goal` is the [plan.md](plan.md) goal that delivers the requirement. `Later` means after G3.

### Functional Requirements

| ID | Requirement | Priority | Goal | Description |
|---|---|---|---|---|
| FR-10 | **Docker run** | Critical | G0 | `docker compose up` on a clean machine starts prei; observability is optional |
| FR-11 | **Seeded market** | Critical | G0 | One command loads one market (growth areas with GACS, properties, rent inputs) into the container |
| FR-12 | **Journey acceptance, steps 1–4** | Critical | G1 | Identify, discover, screen and underwrite on the seeded market |
| FR-13 | **Journey acceptance, steps 5–7** | Critical | G2 | Offer, acquire and own: an acquired deal appears in the portfolio with complete data |
| FR-14 | **Journey acceptance, steps 8–9** | High | G3 | BRRRR and leasing on an acquired property |
| FR-1 | **Rentcast Integration** | Later | Later | Add a Rentcast adapter to the rent chain, only if G1's measurement shows HUD FMR is not good enough |
| FR-2 | **ATTOM Rent Fields** | Later | Later | Test whether ATTOM returns rent estimates; if yes, add as a fallback |
| FR-3 | **GACS Backtest & Validation** | Later | Later | Backtest GACS against FHFA/Zillow appreciation; publish weight sensitivity and confidence bands |
| FR-4 | **GACS Signal Completion** | Later | Later | School quality, supply constraint from permits, county QCEW employment |
| FR-5 | **Real Crime Data** | Later | Later | FBI CDE retry; else SpotCrime, CityProtect or local PD APIs |
| FR-7 | **Async work** | High | G1 if needed | Async re-screen, discovery and VRM scrape, only if G1 shows a request timing out |
| FR-9 | **CSP & Security Headers** | High | In flight (#458), then Later | Django 6 built-in `ContentSecurityPolicyMiddleware` (nonce-based); CSP, Permissions-Policy, Cross-Origin-Resource-Policy; SRI on external scripts |

### Non-Functional Requirements

| ID | Requirement | Priority | Goal | Description |
|---|---|---|---|---|
| NFR-7 | **Rent data measured** | Critical | G1 | Coverage by source on the seeded market, and HUD FMR vs Rentcast quality for Rentcast's fee, recorded in `docs/assessments/` |
| NFR-1 | **Rent coverage ≥ 90%** | High | G1 target | ≥90% of seeded properties have a rent estimate for screening |
| NFR-4 | **Async task latency < 5s** | High | G1 if needed | User-visible screening re-run under 5s |
| NFR-2 | **GACS predictive validity** | Later | Later | Backtest R² ≥ 0.4 vs 12-month appreciation; publish methodology |
| NFR-3 | **Crime data granularity** | Later | Later | ZIP or census-tract level |
| NFR-6 | **Zero-downtime deploy** | Later | Later | Only with a hosted deploy; canary is a VISION non-goal |

---

## Acceptance Criteria

| ID | Criterion | Test Type | Goal |
|---|---|---|---|
| AC-10 | On a clean checkout, `docker compose up` plus the seed command gives a healthy `/health/` | live-system (container) | G0 |
| AC-11 | `tests/acceptance/` passes with `BASE_URL` pointing at the container | live-system (container) | G0 |
| AC-12 | A journey scenario for steps 1–4 passes against the container | acceptance | G1 |
| AC-13 | Rent measurement report committed, with coverage by source and a Rentcast recommendation | file exists | G1 |
| AC-14 | A journey scenario for steps 5–7 passes against the container | acceptance | G2 |
| AC-15 | Scenarios for BRRRR and leasing on an acquired property pass against the container | acceptance | G3 |
| AC-8 | CSP header present on all responses | live-system | In flight (#458) |
| AC-1, AC-2, AC-3, AC-4, AC-6, AC-9 | Rentcast, HUD fallback, GACS backtest, crime, async, SRI (unchanged from the superseded spec) | as before | Later |

---

## Constraints

1. **Decimal money**: all rent and currency stays Decimal.
2. **Service-layer boundaries**: new adapters in `core/integrations/sources/`.
3. **No Bootstrap**: custom design system only ([DESIGN.md](DESIGN.md)).
4. **Docker first**: the container image is the artifact; a hosted deploy comes later.
5. **Free keys on the critical path**: paid APIs only after measurement.
6. **Single-user**: no teams or sharing.

---

## Out of Scope

- Hosted deploy (Render or other) until after G3
- Mobile app / PWA enhancements
- MLS/RESO integration, tax strategy, 1031 exchange tracking
- Team or shared pipelines, lender/agent deal sharing
- Postgres for local runs

---

## Governance Alignment

- **KNOWN_LIMITATIONS.md**: G0 resolves LIMIT-17; G1 re-checks LIMIT-11 and LIMIT-15; G2 resolves LIMIT-12.
- **CHANGE_IMPACT_MAP.md**: update when seed or rent code changes.
