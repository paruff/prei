# Underwriting Deals

> Analyze a deal financially before making an offer. prei has two underwriting tools:
> pipeline underwriting (per-property) and the standalone BRRRR calculator.

---

## Two Underwriting Tools

| | **Pipeline Underwriting** | **BRRRR Calculator** |
|---|---|---|
| **Context** | A property in your pipeline | Standalone deal analysis |
| **Where** | Pipeline detail (`/pipeline/<pk>/`) | `/brrrr/` |
| **Rent source** | Property data (VRM / HUD FMR fallback) | Manual input |
| **Rehab** | Optional (part of CoC denominator) | Required input |
| **Refinance** | Not modeled | Full refi modeling |
| **Target metric** | Cap rate threshold → MAO | DSCR + cash recycle verdict |
| **Best for** | Buy-and-hold evaluation | BRRRR strategy deals |

---

## 1. Pipeline Underwriting

**When:** after a property passes screening, click **→ Underwriting** in the screener
to move it to the UNDERWRITING stage, then open its pipeline detail page.

### Inputs

From the property record plus your assumptions:

- **Estimated rent** (monthly) — from VRM source or HUD FMR fallback
- **Purchase price**
- **Property tax** (annual) and **insurance** (annual)
- **Vacancy rate** — default 5%
- **Rehab budget**
- **Maintenance reserve rate** — default 10% of GPR
- **Management fee rate** — default 8% of EGI
- **HOA** (annual)

### Metrics computed

| # | Metric | Formula |
|---|---|---|
| 1 | **Gross Potential Rent (GPR)** | monthly rent × 12 |
| 2 | **Effective Gross Income (EGI)** | GPR × (1 − vacancy rate) |
| 3 | **Operating Expenses** | tax + insurance + (GPR × maint%) + (EGI × mgmt%) + HOA |
| 4 | **Net Operating Income (NOI)** | EGI − OpEx |
| 5 | **Cap Rate** | NOI / purchase price |
| 6 | **Cash-on-Cash** | NOI / (price + rehab) — all-cash baseline |
| 7 | **Max Allowable Offer (MAO)** | NOI / target cap rate |

### Target cap rate & MAO

- You supply a **target cap rate** (e.g., 8%).
- MAO **backsolves** the maximum price that still hits that cap rate: `MAO = NOI / target`.
- If the asking price is above MAO, the deal doesn't meet your return threshold.

### Interpretation

- **Cap Rate ≥ target** — the deal meets your return bar.
- **Cash-on-Cash** — the unlevered return on your all-in cost (price + rehab).
- **MAO** — the max price you should offer; negotiate down from here.

---

## 2. BRRRR Calculator

The BRRRR (Buy, Rehab, Rent, Refinance, Repeat) calculator is a **client-side** tool
that models the full refi cycle. It is covered in detail in its own guide:
[Using the BRRRR Calculator](use-brrrr-calculator.md).

### Inputs (summary)

Purchase price, ARV (**required**), rehab cost, closing costs %, monthly rent,
refinance LTV (default 75%), refi rate/term, and annual operating expenses.

### Outputs & verdicts (summary)

| Metric / Verdict | Condition | Meaning |
|---|---|---|
| **Total Project Cost** | purchase + rehab + closing | All-in capital |
| **Max Refi Loan** | ARV × LTV | Cash-out amount |
| **Cash Left in Deal** | total cost − max loan | Capital still in the deal |
| 🟢 **Full Cycle** | cash left ≤ 0 | All capital recycled — ready for next deal |
| 🟡 **Partial Recycle** | cash left ≤ 25% of project cost | Most capital free; some remains |
| 🔴 **Capital Trap** | cash left > 25% of project cost | Too much capital stuck — renegotiate |
| **DSCR** | NOI / annual debt service | Lender qualification metric |

### DSCR warning

If **DSCR < 1.25**, a warning is appended to the verdict banner — most lenders require
≥ 1.25 to qualify the refinance.

---

## Key Differences Recap

| Aspect | Pipeline Underwriting | BRRRR Calculator |
|--------|----------------------|------------------|
| Context | Property in pipeline | Standalone deal analysis |
| Rent Source | Property data (VRM/FMR) | Manual input |
| Rehab | Optional field | Required input |
| Refinance | Not modeled | Full refi modeling |
| Target | Cap rate threshold | DSCR + cash recycle |
| Best For | Buy-and-hold evaluation | BRRRR strategy deals |

---

## Related

- [Financial KPIs](../reference/financial-kpis.md) — formal definitions of every metric
- [Screening Properties](screen-properties.md) — how properties reach underwriting
- [Pipeline stages](../explanation/investor-workflow.md) — where underwriting fits in
