## Phase 1.4 — Unit Tests for V1 Listing Scorer (`test_scoring.py`)

### User Story
As a developer, I want a comprehensive test suite for the listing scorer so that regressions are caught immediately and boundary conditions are documented.

### Background
`score_listing_v1(listing: Listing) -> Decimal` already exists in `investor_app/finance/utils.py`.  
It computes a score based on:
1. Price per square foot (lower PPSF → higher score)
2. Freshness (recently posted listings get a bonus)

There are **no tests** for this function today.

### Acceptance Criteria
- [ ] Create `core/tests/test_scoring.py`
- [ ] Tests cover **every** branch of `score_listing_v1`:
  - Normal listing (positive price, positive sq_ft, recent posting) → positive score
  - `sq_ft = 0` → score still returns without `ZeroDivisionError`
  - `price = 0` → score still returns (Decimal zero guard)
  - Very old listing (posted 1 year ago) → lower score than a new listing of same price
  - Very large price → score does not overflow or raise
  - Very small price (e.g. `Decimal("1")`) → score does not overflow or raise
- [ ] Each test has a descriptive name and a one-line docstring explaining what it verifies
- [ ] Test file passes `ruff check` with zero violations

### Files to Change
| File | Action |
|------|--------|
| `core/tests/test_scoring.py` | **Create** |

### Implementation Notes
- Use `pytest` and `pytest-django`; follow the patterns in `core/tests/test_finance_utils.py`
- Build `Listing` instances with `Listing(...)` directly (do not hit the database where possible); use `@pytest.mark.django_db` only when needed
- Use `django.utils.timezone.now()` and `datetime.timedelta` for freshness tests
- Import path: `from investor_app.finance.utils import score_listing_v1`

### Definition of Done
- `pytest core/tests/test_scoring.py -v` passes with all tests green
- `ruff check core/tests/test_scoring.py` passes

### Labels
`test` `phase-1` `backend`
