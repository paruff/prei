## Phase 2 — BRRRR Strategy Support (`finance/utils.py` + `core/services/brrrr.py`)

> **Revised Phase:** 2 (promoted from "not in plan")
> **Strategy context:** [`docs/PRODUCT_STRATEGY.md`](../PRODUCT_STRATEGY.md)
> · Tracking issue: open `docs/issues/tracking-product-strategy-pivot.md` as a GitHub issue
> and replace this line with the actual issue number once created.
>
> BRRRR (Buy, Rehab, Rent, Refinance, Repeat) is the dominant wealth-building strategy for
> passive investors scaling from 1 to 10+ properties. See §5 of the product strategy doc.

**Suggested model:** GPT-4.1
**Django version:** Django 4.2 LTS
**Task type:** finance utils functions + service + tests
**Files to edit:** `investor_app/finance/utils.py`, `core/services/brrrr.py` (new), `tests/test_brrrr.py` (new)
**Reference file:** `investor_app/finance/utils.py` (`calculate_monthly_mortgage`, `dscr`)
**Depends on:** CMA engine (#27) for ARV comparable data
**Do not:** Add Django model imports to `finance/utils.py`
**Do not:** Call external APIs from `brrrr.py` — use `core/integrations/`

### User Story

As a passive real estate investor using the BRRRR strategy, I want to analyze whether a
distressed property can be bought, rehabbed, rented, and refinanced to recycle my down payment
into the next deal — so that I can scale my portfolio without deploying additional capital.

### Background

BRRRR (Buy, Rehab, Rent, Refinance, Repeat) works as follows:
1. **Buy** a distressed property below market value
2. **Rehab** to bring it to rent-ready condition
3. **Rent** at market rate
4. **Refinance** at 75% LTV of ARV (After-Repair Value) — this is the "cash-out refi"
5. **Repeat** — use the refinanced equity to fund the next deal

The key question: "How much of my own money did I leave in the deal?" If the cash-out refi
covers the purchase + rehab cost, you've achieved "infinite CoC" (none of your own capital
remains deployed).

**Current state:**
- `calculate_monthly_mortgage()` exists
- `dscr()` exists
- No ARV estimation, rehab cost, or BRRRR-specific functions exist

### Acceptance Criteria

#### `investor_app/finance/utils.py` — Pure math functions

- [ ] `estimate_arv(comparable_sales: list[tuple[Decimal, Decimal]], subject_sqft: Decimal) -> Decimal`
  - `comparable_sales` is a list of `(price, sqft)` tuples — one entry per comparable sale
  - Computes `median_ppsf` from all comps: `median([price / sqft for price, sqft in comparable_sales])`
  - Returns `median_ppsf × subject_sqft`
  - Raises `ValueError` if `comparable_sales` is empty
  - Raises `ValueError` if any comp has `sqft <= 0` or `price <= 0`
  - Raises `ValueError` if `subject_sqft <= 0`

- [ ] `estimate_rehab_cost(sqft: Decimal, renovation_level: str, cost_per_sqft: dict[str, Decimal]) -> Decimal`
  - `renovation_level` must be one of: `"cosmetic"`, `"moderate"`, `"full_gut"`
  - `cost_per_sqft` is a plain dict mapping renovation level to cost (e.g. `{"cosmetic": Decimal("15"), ...}`)
  - Returns `cost_per_sqft[renovation_level] × sqft`
  - Raises `ValueError` for unknown `renovation_level`
  - Raises `ValueError` if `sqft <= 0`
  - Note: the service layer (`core/services/brrrr.py`) should supply `cost_per_sqft` from
    `settings.REHAB_COST_PER_SQFT` so the pure function stays Django-free

- [ ] `max_refinance_loan(arv: Decimal, ltv_ratio: Decimal = Decimal("0.75")) -> Decimal`
  - Returns `arv × ltv_ratio` (maximum loan at given LTV)
  - Raises `ValueError` if `ltv_ratio` not in `(0, 1)`
  - Raises `ValueError` if `arv <= 0`

- [ ] `cash_left_in_deal(purchase_price: Decimal, rehab_cost: Decimal, cash_out_refi_amount: Decimal, closing_costs: Decimal = Decimal("0")) -> Decimal`
  - Returns `purchase_price + rehab_cost + closing_costs - cash_out_refi_amount`
  - Negative or zero result = "infinite CoC" — investor recouped all capital

- [ ] `brrrr_coc_return(annual_net_cash_flow: Decimal, cash_left_in_deal: Decimal) -> Decimal`
  - If `cash_left_in_deal <= 0`: returns `Decimal("Infinity")` (investor recouped all capital —
    this is the infinite CoC scenario regardless of cash flow value)
  - If `cash_left_in_deal > 0` and `annual_net_cash_flow == 0`: returns `Decimal("0")`
    (no cash flow with capital still in the deal = 0% CoC return)
  - Otherwise: returns `annual_net_cash_flow / cash_left_in_deal`

#### `core/services/brrrr.py` (new)

- [ ] `analyze_brrrr_deal(listing_id: int, renovation_level: str, comparable_listing_ids: list[int]) -> dict`
  - Fetches `Listing` and comparables from DB; builds `comparable_sales` list of `(price, sqft)` tuples
  - Passes `settings.REHAB_COST_PER_SQFT` as `cost_per_sqft` to `estimate_rehab_cost()`
  - Calls pure finance functions above
  - Returns dict: `arv`, `rehab_cost`, `max_refi_loan`, `cash_left_in_deal`, `infinite_coc` (bool), `post_refi_dscr`, `monthly_cash_flow_post_refi`
  - `post_refi_dscr` uses `dscr()` from `finance/utils.py` with the new refinanced loan

#### Tests

- [ ] `tests/test_brrrr.py`:
  - [ ] `estimate_arv`: empty comps (should raise), single comp, multiple comps with varying sqft, any comp with sqft = 0 (should raise)
  - [ ] `estimate_rehab_cost`: each renovation level, unknown level (should raise), sqft = 0 (should raise)
  - [ ] `max_refinance_loan`: ltv = 0 (should raise), ltv = 1 (should raise), standard 75% LTV
  - [ ] `cash_left_in_deal`: positive (some capital left), zero (breakeven), negative (infinite CoC)
  - [ ] `brrrr_coc_return`: infinite CoC scenario (cash_left ≤ 0), normal scenario (positive cash left and positive cash flow), zero cash flow with positive cash left returns `Decimal("0")`
  - [ ] Boundary: very large purchase price ($500K+)

### Architecture Check

- Pure math in `finance/utils.py` (no Django imports)
- Service in `core/services/brrrr.py` (Django-aware, accesses DB)
- No external API calls from the service — use `core/integrations/market/comps.py` for ARV comparables

### Settings Required

Add to `investor_app/settings.py` (with env var overrides):

```python
REHAB_COST_PER_SQFT = {
    "cosmetic": Decimal("15"),    # paint, carpet, fixtures
    "moderate": Decimal("35"),    # kitchen, baths, flooring
    "full_gut": Decimal("75"),    # structural, mechanicals, full renovation
}
```

These are national averages — document clearly as approximations.

### Notes

- The 75% LTV is the standard for conventional investment property cash-out refinancing (Fannie Mae); expose as a configurable parameter
- "Infinite CoC" is a marketing term in the BRRRR community — return it as a boolean flag plus the actual `cash_left_in_deal` value
- DSCR for the refinanced loan should be ≥ 1.25 for most lenders; surface this as a pass/fail indicator
