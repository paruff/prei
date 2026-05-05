## Phase 2 — Market Selection Scoring (`core/services/market_scoring.py`)

> **Revised Phase:** 2 (promoted from "not in plan")
> **Strategy context:** [`docs/PRODUCT_STRATEGY.md`](../PRODUCT_STRATEGY.md) · Tracking issue: #TRACKING
>
> Top passive investors select markets *before* properties. Market selection intelligence is
> a Phase 2 prerequisite to meaningful deal scoring. See §6 of the product strategy doc.

**Suggested model:** GPT-4.1
**Django version:** Django 4.2 LTS
**Task type:** service function + model field additions + tests
**Files to edit:** `core/services/market_scoring.py` (new), `core/models.py` (extend `MarketSnapshot`), `tests/test_market_scoring.py` (new)
**Reference file:** `core/services/cma.py`, `core/integrations/market/` (existing market adapter pattern)
**Do not:** Call external APIs directly from `market_scoring.py` — use the existing adapter pattern in `core/integrations/market/`
**Do not:** Add financial math to the service — scoring logic that is pure math goes in `investor_app/finance/utils.py`

### User Story

As a passive real estate investor, I want to evaluate a metro market's investment viability
before searching for properties — scoring it on price-to-rent ratio, population trends,
employment diversity, and landlord-friendliness — so that I'm searching in markets where the
fundamentals support long-term rental returns.

### Background

The current `MarketSnapshot` model captures `crime_score` and `school_rating` — these are
tenant-attractiveness metrics (useful for setting rent). What's missing are investor-viability
metrics: whether a market will produce consistent rent growth, retain tenants, and allow
landlords to operate profitably.

**Current state:**
- `MarketSnapshot` model: `zip_code`, `rent_index`, `price_trend`, `crime_score`, `school_rating`
- `refresh_market_snapshot()` service exists (calls 4 market adapters)
- No investor-viability scoring exists

### Acceptance Criteria

#### `core/models.py` — Extend `MarketSnapshot`

- [ ] Add fields to `MarketSnapshot`:
  - `price_to_rent_ratio` — `DecimalField(null=True, blank=True)`: purchase price ÷ annual rent for median SFR in this market
  - `population_growth_rate` — `DecimalField(null=True, blank=True)`: annual % change (positive = growing)
  - `employment_diversity_score` — `DecimalField(null=True, blank=True)`: 0–100; higher = more diverse employer base
  - `landlord_friendliness_score` — `DecimalField(null=True, blank=True)`: 0–100; higher = more landlord-friendly (eviction speed, no rent control)
  - `rent_growth_rate` — `DecimalField(null=True, blank=True)`: annual rent growth %
  - `market_score` — `DecimalField(null=True, blank=True)`: composite investor-viability score 0–100
- [ ] Migration created with rollback path documented in PR

#### `core/services/market_scoring.py` (new)

- [ ] `score_market(snapshot: MarketSnapshot) -> Decimal`
  - Composite score 0–100 from available signals
  - Weights (configurable via `settings.MARKET_SCORE_WEIGHTS`): price_to_rent (25%), population growth (20%), employment diversity (20%), landlord friendliness (25%), rent growth (10%)
  - Returns `Decimal("0")` gracefully when all signals are `None` (don't crash on missing data)
  - Raises `ValueError` only if `snapshot` is `None`

- [ ] `update_market_scores(zip_codes: list[str]) -> int`
  - Calls `score_market()` for each snapshot and saves `market_score` field
  - Returns count of updated records
  - Designed to be called from a Celery task in a future issue

#### `investor_app/finance/utils.py` (if needed)

- [ ] `price_to_rent_ratio(median_home_price: Decimal, annual_median_rent: Decimal) -> Decimal`
  - Raises `ValueError` if `annual_median_rent <= 0`
  - Rule of thumb: < 15 = strong rental market, 15–20 = neutral, > 20 = expensive market

- [ ] All functions/methods have Google-style docstrings and type hints
- [ ] `tests/test_market_scoring.py` covers:
  - [ ] `score_market` with all signals populated — composite in [0, 100]
  - [ ] `score_market` with all signals `None` — returns 0, does not raise
  - [ ] `score_market` with partial signals — returns partial score proportionally
  - [ ] `price_to_rent_ratio` boundary: annual_rent = 0 (should raise)
  - [ ] `price_to_rent_ratio` large values ($500K home, $24K annual rent)
  - [ ] `update_market_scores` with empty list returns 0

### Migration Safety Check

- [ ] Migration is reversible: `./manage.py migrate core <previous_migration>` succeeds
- [ ] All new fields are nullable — no NOT NULL addition to existing rows
- [ ] `./manage.py migrate --run-syncdb` passes on a clean database

### Architecture Check

- `market_scoring.py` calls adapters via the integration layer, not directly
- Financial math (price_to_rent_ratio) in `finance/utils.py`
- `MarketSnapshot` model fields are nullable to support incremental data collection
- Scoring weights in `settings.MARKET_SCORE_WEIGHTS`

### Notes

- For the MVP, `landlord_friendliness_score` can be seeded from a static lookup table by state (e.g., Florida: 85, California: 20, Texas: 90). Document this clearly as a placeholder for future API data.
- `employment_diversity_score` can be derived from BLS data or a static tier list by metro for the MVP
- All scores are 0–100 where higher = better for investors
