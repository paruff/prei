## Phase 2.2 — Neighborhood Insights: Market Adapter Integration Tests

### User Story
As an investor, I want neighborhood market signals (comps, rent estimates, crime, school ratings) stored against a ZIP code so that I can evaluate deal context beyond the listing price.

### Background
The following adapters already exist in `core/integrations/market/`:
- `comps.py` — comparable property data
- `rents.py` — rent estimate data
- `crime.py` — crime score data
- `schools.py` — school rating data

The `MarketSnapshot` model exists in `core/models.py` with fields:
`area_type`, `zip_code`, `city`, `state`, `rent_index`, `price_trend`, `crime_score`, `school_rating`, `updated_at`

There are **no tests** for these adapters or for saving their output to `MarketSnapshot`.

### Acceptance Criteria
- [ ] Create `core/tests/test_neighborhood_insights.py` with:
  - Unit tests for each adapter (`comps`, `rents`, `crime`, `schools`) using mocked HTTP responses (no live network calls)
  - A test that calls all four adapters and upserts results into a `MarketSnapshot` — verifies fields are populated
  - A test for `MarketSnapshot.__str__` with both `zip_code`-only and `city/state`-only variants
- [ ] Create `core/services/market_data.py` with:
  - `refresh_market_snapshot(zip_code: str) -> MarketSnapshot`  
    — calls all four adapters, upserts `MarketSnapshot`, returns the saved instance
  - Guard all adapter calls in `try/except`; log errors and continue with default `Decimal("0")` on failure
- [ ] Tests for `refresh_market_snapshot`:
  - All adapters succeed → snapshot fields populated
  - One adapter raises `Exception` → snapshot still saved with other fields; error logged
- [ ] CI guard: mark live network tests with `@pytest.mark.integration` and skip by default

### Files to Change
| File | Action |
|------|--------|
| `core/services/market_data.py` | **Create** |
| `core/tests/test_neighborhood_insights.py` | **Create** |

### Implementation Notes
- Use `unittest.mock.patch` or `pytest-mock` (`mocker.patch`) for HTTP calls
- Follow `Decimal` precision rules — all monetary/rate values use `Decimal`, not `float`
- Use `MarketSnapshot.objects.update_or_create(zip_code=zip_code, defaults={...})`
- Log with `logging.getLogger(__name__)`
- Google-style docstrings and type hints required

### Definition of Done
- `pytest core/tests/test_neighborhood_insights.py -v` passes (no live network)
- `ruff check core/services/market_data.py core/tests/test_neighborhood_insights.py` passes
- `refresh_market_snapshot` gracefully handles adapter failures (verified with caplog)

### Labels
`enhancement` `test` `phase-2` `backend`
