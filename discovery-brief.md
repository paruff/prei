# Product Discovery Brief — prei

> This is the PRODUCT-LEVEL discovery brief. It describes the product vision,
> jobs-to-be-done, and success criteria. Feature-level briefs go in `features/<slug>/`.

---

## 1. What We Are Building

prei is a **passive residential real estate investment analytics** platform for
buy-and-hold investors. The core workflow: *"I found a rental property. Help me
decide if I should buy it and at what price."*

### Product boundaries (what is IN scope)

- Underwriting math (NOI, cap rate, cash-on-cash, DSCR, IRR)
- Market intelligence (census, BLS, HUD, ATTOM data integration)
- Property discovery (VRM, foreclosure, MLS, county records)
- Pipeline management (discovery → screening → underwriting → offer → close)
- Portfolio tracking (owned properties, rental income, expenses)
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

### Journey 1: Discovery → Decision

```
1. Browse/source properties (discovery page, VRM, foreclosure feeds)
2. Screen against criteria (1% rule, cap rate, cash-on-cash)
3. Deep-analyze top candidates (underwriting score, market data)
4. Compute offer price (MAO, ARV, rehab estimate)
5. Track through pipeline (offer → due diligence → closing)
6. Add to portfolio (rental income, expenses, KPIs)
```

### Journey 2: Portfolio Analysis

```
1. View all owned properties with current KPIs
2. Run BRRRR projection on equity-rich properties
3. Compare refinance options
4. Project hold-period returns (IRR, total return)
```

### Journey 3: Market Intelligence

```
1. Select state/region
2. View growth areas ranked by composite score (employment, population, housing)
3. Compare ZIP-level market snapshots
4. Identify emerging markets before prices rise
```

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
