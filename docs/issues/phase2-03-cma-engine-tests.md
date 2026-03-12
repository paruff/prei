## Phase 2.3 — CMA Engine Tests (`test_cma.py`)

### User Story
As a developer, I want tests for the CMA (Comparative Market Analysis) engine so that the undervalued property detection logic is verified and protected from regressions.

### Background
`core/services/cma.py` exists with:
- `price_per_sqft(listing: Listing) -> Decimal`
- `find_undervalued(listings, threshold) -> Iterable[Tuple[Listing, Decimal]]`

There are **no dedicated tests** for this module today.

### Acceptance Criteria
- [ ] Create `core/tests/test_cma.py` with tests for:

**`price_per_sqft`**
- Normal listing (price=200000, sq_ft=1000) → `Decimal("200.00")`
- `sq_ft = 0` → returns `Decimal("0")` without raising
- `price = 0` → returns `Decimal("0")`
- Very large price / small sq_ft → no overflow

**`find_undervalued`**
- Empty list → returns empty
- All listings same price-per-sqft → none returned (none are below median × threshold)
- One listing clearly cheaper than others → returned as undervalued
- Custom threshold (e.g., `0.5`) → only very cheap listings returned
- Single-listing input → no crash (median of one)
- Listings with `sq_ft = 0` are excluded from the median calculation but don't crash
- At least one assertion on the returned `Decimal` PPSF ratio value

### Files to Change
| File | Action |
|------|--------|
| `core/tests/test_cma.py` | **Create** |

### Implementation Notes
- Build `Listing` objects directly (no DB required; mark `@pytest.mark.django_db` only if needed)
- Import: `from core.services.cma import price_per_sqft, find_undervalued`
- Use `Decimal` for all monetary values; compare with `==` or `pytest.approx`
- Follow patterns in `core/tests/test_finance_utils.py`

### Definition of Done
- `pytest core/tests/test_cma.py -v` passes
- `ruff check core/tests/test_cma.py` passes

### Labels
`test` `phase-2` `backend`
