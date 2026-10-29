# VISION.md (years) — prei

**Product**: prei — passive residential real estate investment analytics for buy-and-hold investors

**North Star**: Empower buy-and-hold residential investors to discover, analyze, acquire, and grow their rental portfolios using data-driven insights — all in one system, without switching between spreadsheets, listing sites, and property management tools.

---

## Users

One investor per account (single-user for now).

- **Buy-and-hold SFR investor (primary):** buys 1–2 properties a year in landlord-friendly states (TX, FL, TN), screens with the 1% rule, cap rate and cash-on-cash, and looks at 100+ properties to find one deal.
- **BRRRR investor:** scales from 1 to 10+ properties by refinancing; needs ARV, rehab budget, refinance projection, IRR and hold-period analysis.
- **Data-driven sourcer:** runs discovery pipelines (VRM, foreclosures, county auctions) and batch screening, and uses market data to find emerging ZIPs.

## The investor journey

The product is this journey. Each step names the [plan.md](plan.md) goal that proves it works.

| Step | The investor… | Goal |
|---|---|---|
| 1. Identify | ranks growth areas in a state by composite score (GACS: employment, population, housing demand) | G1 |
| 2. Discover | browses listings in those areas: VRM, foreclosures, sheriff sales, HUD/USDA REO, county records | G1 |
| 3. Screen | kills ~90% of properties cheaply with the 1% rule, GRM, cap rate and cash-on-cash | G1 |
| 4. Underwrite | runs full KPIs (NOI, cap rate, CoC, DSCR) against market cap rates and scores the deal | G1 |
| 5. Offer | computes the maximum allowable offer from ARV, rehab budget and equity target | G2 |
| 6. Acquire | moves the deal through offer, due diligence and closing to acquired | G2 |
| 7. Own | tracks the property in the portfolio: rent, expenses, monthly actuals vs pro forma | G2 |
| 8. Grow | runs BRRRR on equity-rich properties to plan the next purchase | G3 |
| 9. Lease | takes the property from listed through tenant screening to a signed lease | G3 |

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
| `intent.md` | What problem are we solving now, for whom, and within which constraints? | current release |
| `spec.md` | What did we decide to build (requirements, acceptance criteria)? | current release |
| `plan.md` | Goals (one GitHub milestone each), their proof, the issues under them, risks | current release |
| [Project board](https://github.com/users/paruff/projects/3) | What's next for an agent? What waits on a human? (status lives only here) | today |
| `docs/ARCHITECTURE.md` | Layer rules and dependency diagram | years |
| `docs/KNOWN_LIMITATIONS.md` | Active known issues and workarounds | years |
| `docs/CHANGE_IMPACT_MAP.md` | Co-change map for models, services, finance utils | years |
| `docs/DEPLOYMENT_STRATEGY.md` | Canary deployment plan, rollback triggers, migration path | years |
