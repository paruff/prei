## Phase 1.3 — Listing Filters & Query API (`core/filters.py`)

### User Story
As an investor, I want to filter listings by price range, property type, number of bedrooms, and location so that I only see deals that match my investment criteria.

### Background
The `Listing` model already exists in `core/models.py` with fields `price`, `property_type`, `beds`, `city`, `state`, `zip_code`.  
The `dashboard` view in `core/views.py` already applies ad-hoc `price__gte`/`lte` and `state__iexact` filters inline.  
The `search_listings` view in `core/views.py` also does inline filtering.  

This issue centralises all filtering logic into a single, reusable `ListingFilter` class.

### Acceptance Criteria
- [ ] Create `core/filters.py` with a `ListingFilter` class that accepts:
  - `min_price` / `max_price` (Decimal)
  - `property_type` (string, case-insensitive)
  - `beds` (integer, minimum)
  - `state` (string, case-insensitive)
  - `zip_code` (string)
  - `query` (searches `address` and `city` via `icontains`)
- [ ] `ListingFilter.apply(queryset)` returns a filtered `QuerySet[Listing]`
- [ ] Replace the inline filter logic in `dashboard` and `search_listings` views with `ListingFilter`
- [ ] Unit tests in `core/tests/test_filters.py` cover:
  - happy path for each filter param
  - empty queryset when no listings match
  - multiple filters combined
  - case-insensitivity for `state` and `property_type`

### Files to Change
| File | Action |
|------|--------|
| `core/filters.py` | **Create** — `ListingFilter` class |
| `core/views.py` | **Edit** — replace inline filter logic in `dashboard` and `search_listings` with `ListingFilter` |
| `core/tests/test_filters.py` | **Create** — unit tests |

### Implementation Notes
- Use only Django ORM; no external library (e.g. django-filter) unless already in `requirements.txt`
- All fields are optional; omitting a field means no filter on that field
- Guard against invalid Decimal inputs (catch `ValueError`/`InvalidOperation` and ignore that filter param)
- Follow Google-style docstrings
- All functions need type hints

### Definition of Done
- `pytest core/tests/test_filters.py -q` passes
- `ruff check core/filters.py core/tests/test_filters.py` passes with zero violations
- `dashboard` and `search_listings` views produce identical results to the current inline logic

### Labels
`enhancement` `phase-1` `backend`
