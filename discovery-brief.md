# Product Discovery Brief — prei

> This is the PRODUCT-LEVEL discovery brief. It describes the product vision,
> jobs-to-be-done, and success criteria. Feature-level briefs go in `features/<slug>/`.

---

## 1. What We Are Building

prei is a **passive residential real estate investment analytics** platform for
buy-and-hold investors. The core workflow spans the full investor lifecycle:

**"I want to find a cash-flowing rental property in a growing market, analyze it
against my investment criteria, manage the offer and closing process, track its
performance in my portfolio, and eventually lease it out — all in one system."**

### Product boundaries (what is IN scope)

- **Growth area identification** — composite scoring (employment, population,
  housing demand) to surface emerging markets before prices rise
- **Property discovery** — VRM feed, foreclosure notices, sheriff sales, HUD REO,
  USDA REO, county records across TX, FL, and other landlord-friendly states
- **Screening** — 1% rule, GRM, cap rate, cash-on-cash filters to kill bad deals
  early and cheaply before investing analyst time
- **Underwriting** — full KPI analysis (NOI, cap rate, cash-on-cash, DSCR, IRR)
  with market-aware cap rate comparison and deal scoring
- **BRRRR analysis** — Buy/Rehab/Rent/Refinance/Repeat projection with ARV
  estimation, rehab budgeting, refinance modeling, and hold-period returns
- **Offer management** — MAO calculation, offer price optimization with
  competition multiplier and equity constraints
- **Acquisition pipeline** — CRM-like stage tracking (discovery → screening →
  underwriting → offer → due diligence → closing → acquired)
- **Portfolio tracking** — owned properties with rental income, operating expenses,
  monthly actuals, investment analysis, and hold-period projections
- **Leasing pipeline** — separate workflow for rent-ready properties: listing,
  tenant screening, lease signing, rent collection tracking
- BRRRR analysis (buy, rehab, rent, refinance, repeat projection)
- Deal comparison and ranking

### What is NOT in scope

- Active stock/REIT trading
- Commercial property (>4 units multifamily, office, retail)
- Real-time auction bidding
- Property management (tenant portals, maintenance tickets)
- Legal/tax advice

---

## 2. User Personas

### Primary: Buy-and-Hold SFR Investor

- Purchases 1-2 properties per year
- Looks for cash-flow positive deals in landlord-friendly states (TX, FL, TN)
- Uses 1% rule, cap rate, cash-on-cash as primary screens
- Needs to evaluate 100+ properties to find 1-2 deals

### Secondary: BRRRR Investor

- Scales from 1 to 10+ properties through refinancing
- Needs ARV estimation, rehab budget, refinance projection
- More sophisticated: uses IRR, NPV, hold-period analysis

### Tertiary: Data-Driven Sourcer

- Builds custom discovery pipelines (VRM, foreclosure, county auctions)
- Needs batch screening against investment criteria
- Uses market intelligence to identify emerging ZIPs

---

## 3. Core User Journeys

### Journey 1: Full Investment Lifecycle (Primary)

```
1. IDENTIFY growth areas — select state, run GACS analysis, rank markets
   by composite score (employment growth, population growth, housing demand)
2. DISCOVER properties — browse growth area listings, VRM feed, foreclosure
   notices, sheriff sales, HUD/USDA REO properties
3. SCREEN for profitability — apply 1% rule, GRM, cap rate threshold;
   kill 90% of properties here (cheaply, before analyst time)
4. UNDERWRITE top candidates — full KPI analysis: NOI, cap rate,
   cash-on-cash, DSCR; compare against market cap rates; score deals
5. COMPUTE offer price — MAO (maximum allowable offer) with ARV estimate,
   rehab budget, desired equity target, competition multiplier
6. TRACK through acquisition pipeline — offer submitted → due diligence
   → closing → acquired; manage documents and deadlines
7. ADD to portfolio — record purchase price, rental income, operating
   expenses; track monthly actuals against pro-forma
8. RUN BRRRR analysis — identify equity-rich properties; project
   refinance returns; plan next acquisition
9. LEASE the property — move acquired property through leasing pipeline:
   list → screen tenants → sign lease → track rent collection
```

### Journey 2: Market Intelligence (Discover Where to Buy)

```
1. Select target state/region
2. Run growth area analysis against census + BLS + HUD data
3. View ranked markets by composite score
4. Drill into ZIP-level market snapshots (schools, crime, rents, comps)
5. Identify emerging markets before prices rise
6. Set saved searches and alerts for target areas
```

### Journey 3: Portfolio Analysis

---

## 4. Technical Constraints (from ARCHITECTURE.md)

- **Decimal money** — all currency is Decimal, never float
- **Service-layer boundaries** — views call services, services call models
- **No external API calls from views** — always through integrations/
- **No Bootstrap** — custom design system with CSS custom properties
- **SQLite for development** — Postgres reserved for production
- **GitOps deployment** — Docker image is the artifact, manifests in git

---

## 5. Success Criteria

| Metric | Target | How measured |
|---|---|---|
| CI/CD gate pass rate | 100% on main | GitHub Actions |
| Test coverage | ≥70% line, ≥90% branch on finance/ | pytest-cov |
| Build time | <10 minutes | docker-publish.yml job-start/job-finish |
| Deploy frequency | ≥1/day when active | DORA metrics |
| Change failure rate | ≤15% | DORA metrics |
| All core KPIs verified | 8 of 8 functions | tests/test_finance_math.py (58 cases) |

---

## 6. Current Feature Status

See `features/` directory for archived per-feature specs, designs, and tasks.
Active feature work is at `specification.md`, `design.md`, `tasks.json` at repo root.

## 7. Related Docs

| Doc | Purpose |
|---|---|
| `docs/ARCHITECTURE.md` | Layer rules and dependency diagram |
| `docs/planning/PRODUCT_STRATEGY.md` | PM critique and implementation history |
| `docs/KNOWN_LIMITATIONS.md` | Active issues — read before touching listed areas |
| `docs/DOCS_AUDIT.md` | Documentation alignment audit |
| `docs/TOP_01_PLAN.md` | Quality roadmap (Phases A-D complete) |
