# The prei Investor Workflow

> How buy-and-hold investors move from market selection to deal analysis — and where each guide fits.

---

## Overview

prei organizes investing into four stages. Each stage has a page, a job to do, and a
guide that walks you through it:

| Stage | What you do | Where | Guide |
|---|---|---|---|
| 1. **Growth Areas** | Find markets with strong growth fundamentals | `/growth/`, `/growth-explorer/` | [Analyzing Growth Areas](../how-to-guides/analyze-growth-areas.md) |
| 2. **Discovery** | Source distressed/foreclosure properties in those markets | `/discovery/` | [Discovering Properties](../how-to-guides/discover-properties.md) |
| 3. **Screening** | Filter properties against your buy criteria | `/pipeline/screener/` | [Screening Properties](../how-to-guides/screen-properties.md) |
| 4. **Underwriting** | Analyze deals financially before making an offer | `/pipeline/<pk>/`, `/brrrr/` | [Underwriting Deals](../how-to-guides/underwrite-deals.md) |

The flow is sequential but not mandatory — you can add properties manually, screen them,
and skip straight to underwriting. The pages simply connect when you follow the full path.

---

## Stage 1: Growth Areas

**Goal:** identify cities with rising employment, population, income, and school quality.

- **What is GACS?** The Growth Area Composite Score — see the
  [GACS Guide](GACS_GUIDE.md) for a deep dive on the 7 weighted signals.
- **How to explore:** use the [Growth Explorer](../how-to-guides/analyze-growth-areas.md)
  to analyze the top cities in any state, or browse the ranked
  [Growth Areas list](../how-to-guides/analyze-growth-areas.md).
- **Data confidence:** each score shows a confidence % — how many of the 7 signals
  have real data vs. defaults. Configure `FRED_API_KEY` and `HUD_API_KEY` for full
  coverage.
- **Limitations:** scores use an experimental weighting model, and employment growth
  prefers county-level QCEW data with a state-level FRED fallback. Use GACS to rank
  markets, not to predict prices.

## Stage 2: Discovery

**Goal:** source distressed and foreclosure properties in a chosen growth area.

- **Source types:** HUD REO, USDA REO, VRM (VA REO), ATTOM pre-foreclosure, and
  County foreclosure notices — see [Discovering Properties](../how-to-guides/discover-properties.md).
- **How it works:** pick a growth area, choose which sources to query, and run
  discovery. Matching records become `PipelineProperty` records in your pipeline.
- **Results:** discovery renders **in-page** on the discovery page with KPI cards and
  per-source results; a "View in Screener" button takes you to the screener. VRM
  scraping runs in a background thread when no VA listings exist yet.

## Stage 3: Screening

**Goal:** filter pipeline properties against criteria you define.

- **Setting criteria:** configure hard kills (state, property type, price, foreclosure
  status) and soft criteria (GACS score, gross yield, price-to-rent, year built, beds)
  at [Screening Settings](../how-to-guides/screen-properties.md).
- **Hard vs. soft:** a hard-kill failure removes the property immediately. Soft criteria
  deduct points from a starting score of 100 — properties with a final score ≥ 50 pass.
- **Review & act:** the [Screener](../how-to-guides/screen-properties.md) shows pass/fail
  status, lets you filter, re-screen all, advance passed properties to underwriting, or
  kill properties with a reason.

## Stage 4: Underwriting

**Goal:** decide whether a deal meets your return targets.

- **Pipeline underwriting:** per-property analysis computes GPR, EGI, OpEx, NOI, cap
  rate, cash-on-cash, and a Max Allowable Offer (MAO) — see
  [Underwriting Deals](../how-to-guides/underwrite-deals.md).
- **BRRRR calculator:** standalone deal-level tool for the Buy-Rehab-Rent-Refi-Repeat
  strategy, with verdicts (Full Cycle / Partial Recycle / Capital Trap) and DSCR
  warnings — see [Using the BRRRR Calculator](../how-to-guides/use-brrrr-calculator.md).
- **Beyond underwriting:** once a deal passes, move it to Offer → Due Diligence →
  Renovation → Closing in the pipeline kanban.

---

## Navigation Map

```
Growth Areas (/growth/)  ──►  Growth Explorer (/growth-explorer/)
        │  "Discover Properties" button
        ▼
Property Discovery (/discovery/?growth_area_id=X)
        │  POST → sources queried, results render in-page
        │  "View in Screener" button
        ▼
Pipeline Screener (/pipeline/screener/?growth_area_id=X)
        │  "→ Underwriting" action (passed properties)
        ▼
Pipeline Detail (/pipeline/<pk>/)  ──►  BRRRR Calculator (/brrrr/)  [standalone]
        │
        ▼
Offer → Due Diligence → Renovation → Closing  (pipeline kanban stages)
```

## Related References

- [Data Sources & API Keys](../reference/data-sources.md) — keys needed per stage
- [Financial KPIs](../reference/financial-kpis.md) — definitions of every metric
- [UI Patterns](../reference/ui-patterns.md) — how prei's interface is built
- [Getting Started Tutorial](../tutorials/getting-started.md) — end-to-end first run
