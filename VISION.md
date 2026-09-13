# VISION.md (years) — prei

**Product**: prei — passive residential real estate investment analytics for buy-and-hold investors

**North Star**: Empower buy-and-hold residential investors to discover, analyze, acquire, and grow their rental portfolios using data-driven insights — all in one system, without switching between spreadsheets, listing sites, and property management tools.

---

## Core Principles (4–8, specific to this product)

1. **Decimal-first money** — All currency uses `Decimal`; never float. Financial NFI (Net Financial Index) calculations are precise to the penny.
2. **Service-layer boundaries** — Views call services; services call models. No business logic in templates or views.
3. **No Bootstrap** — Custom design system with CSS custom properties (`tokens.css` + `base.css`). No third-party CSS frameworks.
4. **SQLite for development, Postgres for production** — Development parity with production-grade data store; zero code changes needed when migrating.
5. **GitOps deployment** — Docker image is the sole artifact; desired state lives in git. No manual deploys.
6. **Investor-first UX** — All documentation, guides, and UI written for buy-and-hold SFR investors, not developers. Tone: practical, jargon-light, decision-focused.
7. **Data confidence prominently** — Every guide and UI surfacing scores/metrics includes data confidence indicators and known limitations.
8. **One system, full lifecycle** — From growth area identification → property discovery → screening → underwriting → acquisition → portfolio tracking → leasing. No stitching together separate tools.

---

## Non-Goals (Current Stage — alpha)

- Active stock/REIT trading
- Commercial property (>4 units, office, retail)
- Real-time auction bidding
- Property management (maintenance tickets, tenant portals)
- Legal/tax advice
- Multi-user team sharing
- Kubernetes / canary deployments (post-MVP only)
- API reference documentation (separate surface)

---

## The Single Riskiest Assumption

**GACS growth data can be populated automatically before users need it.** The entire investor workflow (Growth Areas → Discovery → Screening → Underwriting) depends on Growth Area Composite Scores being available. If `populate_growth_areas` management command does not produce valid GACS scores at deployment, the screening criterion `min_gacs_score` is silently skipped, and users lose a primary filter. This assumption is currently unproven in alpha — the `populate_growth_areas` command may not have been run, and GACS scores may be missing for target markets.

---

## How This Connects

| Doc | What it answers | Reference |
|---|---|---|
| `MILESTONES.md` | What milestones are we targeting over the next 3–6 months? | months |
| `EXECUTION_QUEUE.md` | What is the weekly priority queue? | weeks |
| `plan-for-the-day.md` | What are we doing today? | today |
| `docs/ARCHITECTURE.md` | Layer rules and dependency diagram | years |
| `docs/KNOWN_LIMITATIONS.md` | Active known issues and workarounds | years |
| `docs/CHANGE_IMPACT_MAP.md` | Co-change map for models, services, finance utils | years |
| `docs/DEPLOYMENT_STRATEGY.md` | Canary deployment plan, rollback triggers, migration path | years |
