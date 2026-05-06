## Phase 1 — Underwriting Score v2: Replace `score_listing_v1`

> **Revised Phase:** 1 (replace placeholder with investor-grade scoring)
> **Strategy context:** [`docs/PRODUCT_STRATEGY.md`](../PRODUCT_STRATEGY.md)
> · Tracking issue: open `docs/issues/tracking-product-strategy-pivot.md` as a GitHub issue
> and replace this line with the actual issue number once created.
>
> `score_listing_v1` (PPSF + freshness) is a placeholder. This issue replaces it with a
> multi-signal underwriting score that reflects how passive investors actually evaluate deals.
> See §2 of the product strategy doc.

**Suggested model:** GPT-4.1
**Django version:** Django 4.2 LTS
**Task type:** finance utils function + tests
**Files to edit:** `investor_app/finance/utils.py`, `tests/test_underwriting_score.py` (new)
**Reference file:** `investor_app/finance/utils.py` — `score_listing_v1` (to be replaced/superseded)
**Do not:** Delete `score_listing_v1` — deprecate it by adding a docstring note pointing to the new function; removal is a separate issue after dependents are migrated
**Do not:** Add Django model imports to `finance/utils.py`

### User Story

As a passive real estate investor, I want listings ranked by a multi-signal underwriting score
that reflects real buy/no-buy criteria — the 1% Rule, Gross Rent Multiplier, cap rate vs. local
market, and projected cash-on-cash return — so that the best passive investing opportunities
appear at the top of my list.

### Background

`score_listing_v1` uses two signals: price-per-square-foot and listing freshness. These are
deal-sourcing signals (useful for finding underpriced listings), not underwriting signals
(useful for deciding whether to buy a rental property). A passive investor cares about:

1. **1% Rule** — monthly rent ≥ 1% of purchase price; instant pass/fail filter
2. **GRM (Gross Rent Multiplier)** — purchase price ÷ annual rent; lower is better; market-comparable
3. **Cap Rate vs. local market cap rate** — is this deal above or below the prevailing market rate?
4. **Projected CoC (Cash-on-Cash) at Year 1, 3, 5** — net cash flow ÷ cash invested

**Current state:**
- `score_listing_v1(listing)` exists with Django model dependency
- `cap_rate()`, `cash_on_cash()`, `calculate_monthly_mortgage()` all exist in `finance/utils.py`

### Acceptance Criteria

- [ ] `one_percent_rule(monthly_rent: Decimal, purchase_price: Decimal) -> bool`
  - Returns `True` if `monthly_rent / purchase_price >= Decimal("0.01")`
  - Raises `ValueError` if `purchase_price <= 0`

- [ ] `gross_rent_multiplier(purchase_price: Decimal, annual_rent: Decimal) -> Decimal`
  - Returns `purchase_price / annual_rent`
  - Raises `ValueError` if `annual_rent <= 0`

- [ ] `score_listing_v2(purchase_price: Decimal, monthly_rent: Decimal, annual_noi: Decimal, local_market_cap_rate: Decimal, down_payment: Decimal, annual_debt_service: Decimal) -> dict`
  - Returns a dict with keys: `one_percent_rule_pass` (bool), `grm` (Decimal), `cap_rate` (Decimal), `cap_rate_vs_market` (Decimal — difference from local market, positive = above market), `coc_year1` (Decimal), `composite_score` (Decimal, 0–100)
  - `composite_score` weights: 1% rule (20%), cap rate vs market (30%), CoC year 1 (30%), GRM relative percentile (20%)
  - A deal that fails the 1% rule gets a composite score penalty (score capped at 40)
  - Raises `ValueError` with clear message if any price/income input is ≤ 0

- [ ] `score_listing_v1` is NOT deleted — add deprecation docstring: `"Deprecated: use score_listing_v2 for passive investing use cases. Will be removed after all callers are migrated."`

- [ ] All functions have Google-style docstrings and type hints
- [ ] `tests/test_underwriting_score.py` covers:
  - [ ] 1% Rule: monthly_rent exactly at threshold (1%), above, below
  - [ ] 1% Rule: purchase_price = 0 (should raise)
  - [ ] GRM: annual_rent = 0 (should raise)
  - [ ] `score_listing_v2`: all inputs at realistic values; verify composite score is in [0, 100]
  - [ ] `score_listing_v2`: failing the 1% rule caps composite score at ≤ 40
  - [ ] `score_listing_v2`: above-market cap rate raises composite score vs. below-market
  - [ ] Boundary: very large purchase price ($10M)
  - [ ] Negative: any price/income input ≤ 0 raises `ValueError`

### Architecture Check

- `score_listing_v2` takes plain `Decimal` inputs — no Django model types
- `score_listing_v1` retained (deprecated, not deleted)
- No Django imports added to `finance/utils.py`
- `local_market_cap_rate` comes from `MarketSnapshot` at the service layer, not inside this function

### Notes

- Composite score weighting is a starting point; weights should be configurable via `settings.UNDERWRITING_SCORE_WEIGHTS` (dict) in future — for now, hardcode with a clear comment
- GRM percentile scoring requires a market baseline; for now, use a heuristic: GRM < 10 → excellent, 10–15 → good, 15–20 → fair, > 20 → poor
- CoC Year 3 and Year 5 projections (using `project_annual_cash_flows`) can be added as a follow-on once the hold-period issue is implemented
