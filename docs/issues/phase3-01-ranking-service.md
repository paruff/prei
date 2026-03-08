## Phase 3.2 — Lead Ranking Service (`core/services/ranking.py`)

### User Story
As an investor, I want listings ranked by multiple signals — score, price trend, school rating, crime score, freshness — so that the best leads appear at the top of my list without manual sorting.

### Background
- `score_listing_v1` exists in `investor_app/finance/utils.py` (PPSF + freshness)
- `MarketSnapshot` exists in `core/models.py` (rent_index, price_trend, crime_score, school_rating)
- Phase 2.2 adds `refresh_market_snapshot`
- The `search_listings` view in `core/views.py` already accepts `sort` parameter but only uses `score`

### Acceptance Criteria
- [ ] Create `core/services/ranking.py` with:
  - `rank_listings(listings: QuerySet, market_snapshots: dict[str, MarketSnapshot] | None = None) -> list[dict]`  
    Returns a list sorted by composite score, each item:
    ```python
    {
        "listing": Listing,
        "score_v1": Decimal,
        "market_bonus": Decimal,   # from snapshot signals
        "composite_score": Decimal,
        "category": str,           # "hot" | "good" | "watch" | "pass"
    }
    ```
  - Composite score formula (all Decimal, weights from `settings.RANKING_WEIGHTS`):
    - `composite = score_v1 * w_score + rent_index_bonus * w_rent + school_bonus * w_school - crime_penalty * w_crime`
  - Category thresholds: `hot >= 80`, `good >= 50`, `watch >= 20`, else `pass`
  - `w_score`, `w_rent`, `w_school`, `w_crime` default values added to `investor_app/settings.py` as `RANKING_WEIGHTS`
- [ ] Unit tests in `core/tests/test_ranking.py`:
  - Listings with no market snapshot → ranked by `score_v1` only, `market_bonus = Decimal("0")`
  - Listing with good school rating and low crime → higher composite than identical listing without snapshot
  - Category assignment: verify "hot", "good", "watch", "pass" for known scores
  - Empty listing list → returns empty list without error
  - Custom `RANKING_WEIGHTS` override → composite changes accordingly
- [ ] Update `search_listings` view to call `rank_listings` when `sort=composite`

### Files to Change
| File | Action |
|------|--------|
| `core/services/ranking.py` | **Create** |
| `investor_app/settings.py` | **Edit** — add `RANKING_WEIGHTS` dict |
| `core/views.py` | **Edit** — use `rank_listings` in `search_listings` for `sort=composite` |
| `core/tests/test_ranking.py` | **Create** |

### Implementation Notes
- All weights are `Decimal`; store as strings in settings and convert with `Decimal(str(...))`
- No database writes in the ranking service; it is a pure computation
- Guard all divisions and score bonuses with zero-checks
- Type hints and Google-style docstrings required

### Definition of Done
- `pytest core/tests/test_ranking.py -v` passes
- `ruff check core/services/ranking.py core/tests/test_ranking.py` passes
- `search_listings?sort=composite` returns listings in composite order

### Labels
`enhancement` `phase-3` `backend`
