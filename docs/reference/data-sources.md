# Data Sources — prei

This document catalogs all data sources used by prei for market intelligence, property
valuation, and investor analytics.

---

## Market Scoring Data

Used by the **Markets** page (`/markets/`) and `core/services/market_scoring.py` to compute
market scores per ZIP code.

| Data Point | Source | Type | Update Frequency |
|---|---|---|---|
| Price-to-Rent Ratio | Calculated from property data (purchase price ÷ annual rent) | Derived | Per-property entry |
| Unemployment Rate | Bureau of Labor Statistics (BLS) via public API | External | Monthly |
| Population Growth | US Census Bureau ACS 5-year estimates | External | Annual |
| Employment Diversity | BLS County Employment & Wages | External | Quarterly |
| Market Verdict | Composite score from above signals | Derived | On refresh |

### Market Scoring Weights

| Signal | Weight | Data Source |
|---|---|---|
| Price-to-Rent Ratio | 30% | Property records / Zillow public data |
| Unemployment Rate | 25% | BLS LAUS series |
| Population Growth | 25% | Census ACS |
| Employment Diversity | 20% | BLS QCEW |

### Market Refresh

The `MarketRefreshView` (`/markets/refresh/`) triggers a re-score of all ZIP codes found in the
current user's properties. It scopes to `Property.objects.filter(user=request.user)` — no
cross-user access.

```python
# core/services/market_scoring.py
def score_market_by_zip(zip_code: str) -> dict:
    """Return dict with pr_ratio, verdict, unemployment, pop_growth, overall_score."""
```

---

## Property Financial Data

Used by the **Underwriting Score** engine (`core/services/scoring.py`).

| Data Point | Source | Type |
|---|---|---|
| Purchase Price | User input via Property Form | User-provided |
| Monthly Rent (Gross) | User input via Property Form | User-provided |
| Operating Expenses | User input via Property Form (taxes, insurance, HOA, maint., capex) | User-provided |
| Down Payment % | User input via Property Form | User-provided |
| Interest Rate | User input via Property Form | User-provided |
| Loan Term | User input via Property Form | User-provided |
| Vacancy Rate | User input via Property Form (default 5%) | User-provided |
| Management Fee % | User input via Property Form (default 8%) | User-provided |
| Land Value % | From `UserProfile.land_value_pct` | User-provided |
| Investment Targets | From `UserInvestmentTargets` model | User-provided |

### Derived Metrics

| Metric | Formula | Service |
|---|---|---|
| NOI | Effective Rent - Total Expenses | `investor_app/finance/utils.py` |
| Cap Rate | NOI / Purchase Price | `investor_app/finance/utils.py` |
| Cash-on-Cash | Annual Cash Flow / Down Payment | `investor_app/finance/utils.py` |
| DSCR | NOI / Annual Debt Service | `investor_app/finance/utils.py` |
| GRM | Purchase Price / Annual Rent | `investor_app/finance/utils.py` |
| After-Tax IRR | NPV-based with exit cap scenario | `core/services/projections.py` |
| Depreciation | 27.5-yr straight-line on improvements | `investor_app/finance/utils.py` |

---

## BRRRR Calculation Inputs

Used by the BRRRR Calculator (`core/services/brrrr.py` and `templates/brrrr_calculator.html`).

| Data Point | Source | Notes |
|---|---|---|
| Purchase Price | User input | |
| After-Repair Value (ARV) | User input | Estimated market value post-rehab |
| Rehab Cost | User input | Total renovation budget |
| Closing Costs | User input | Optional, defaults to 0 |
| Refinance LTV % | User input | Default 75% |
| Monthly Rent | User input | Post-rehab expected rent |
| Property Tax | User input | Annual |
| Insurance | User input | Annual |
| Other Expenses | User input | Monthly |
| Down Payment % | User input | |
| Interest Rate | User input | Purchase loan rate |
| Refinance Rate | User input | Cash-out refi rate |

### BRRRR Derived Metrics

| Metric | Formula | Location |
|---|---|---|
| ARV Estimate | `median(comps_ppsf) × subject_sqft` | `investor_app/finance/utils.py` |
| Rehab Cost Estimate | `cost_per_sqft[level] × sqft` | `investor_app/finance/utils.py` |
| Max Refi Loan | `ARV × LTV%` | `investor_app/finance/utils.py` |
| Cash Left in Deal | `purchase + rehab + closing - refi_loan` | `client-side JS + brrrr.py` |
| BRRRR CoC Return | `annual_cf / cash_left` (∞ if ≤ 0) | `investor_app/finance/utils.py` |

---

## External Integrations (Planned)

| Integration | Purpose | Phase |
|---|---|---|
| ATTOM API | Property details, comps, ownership | Phase 4 |
| HUD / FHA | Government-owned property lists | Phase 4 |
| Zillow / Redfin | Public listing data, Zestimate | Phase 4 |
| Census API | Demographics, population trends | Phase 2 (partial via manual data) |
| BLS API | Employment, wage data | Phase 2 (partial via manual data) |

---

## Data Quality Notes

- **User-provided data** is assumed accurate — prei performs no verification against external
  sources.
- **Market data** comes from public, free-tier government APIs or manual entry. Refresh
  timing depends on data source update frequency.
- **BRRRR ARV** is user-estimated or derived from comparable sales; a formal CMA engine is
  planned for Phase 4.
- All currency values use Python `Decimal` — no floats for financial data.
