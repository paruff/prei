## Phase 1.6 — Dashboard Listings View & Integration Tests (`test_views_listings.py`)

### User Story
As an investor, I want the dashboard to show a filtered, scored list of active listings with a quick-save button so that I can act on opportunities without leaving the page.

### Background
- `dashboard` view in `core/views.py` already renders `templates/dashboard.html` and includes some listing query logic
- `score_listing_v1` exists in `investor_app/finance/utils.py`
- `Listing` model has `url`, `address`, `city`, `state`, `price`, `beds`, `baths`, `sq_ft`, `property_type`, `posted_at`
- `SavedSearch` model is available for quick-save
- `ListingFilter` will be added by issue Phase 1.3 — this issue depends on it

### Acceptance Criteria
- [ ] The `dashboard` view passes the top 50 listings (sorted by `score_listing_v1` descending) as `listings` context, each entry a dict with keys: `listing`, `score`
- [ ] `templates/dashboard.html` renders a listings table with columns: Address, Price, Beds/Baths, Sq Ft, Type, Score, Posted, Link
- [ ] Filter form on dashboard accepts `min_price`, `max_price`, `state`, `property_type`, `beds` via GET and passes through to `ListingFilter`
- [ ] "Save Search" button POSTs current filter params and creates/updates a `SavedSearch` for the authenticated user
- [ ] Create `core/tests/test_views_listings.py` with integration tests:
  - Unauthenticated GET `/` redirects to login (or returns 302)
  - Authenticated GET `/` returns HTTP 200 and contains listing data
  - Filter by `state` returns only matching listings
  - Filter by `min_price` / `max_price` returns only in-range listings
  - Score is present and numeric in the response context

### Files to Change
| File | Action |
|------|--------|
| `core/views.py` | **Edit** — update `dashboard` view to use `ListingFilter`, compute scores, sort |
| `templates/dashboard.html` | **Edit** — add listings table and filter form |
| `core/tests/test_views_listings.py` | **Create** |

### Implementation Notes
- Depend on Phase 1.3 (`ListingFilter`) being merged first, or implement inline and refactor
- Use `@login_required` decorator on the view (check if already applied)
- Scores are `Decimal`; format to 2 decimal places in the template with `|floatformat:2`
- Use Django `Client` in tests; create test users and listings via `baker` or direct model construction
- Follow patterns in `core/tests/test_views_dashboard.py`

### Definition of Done
- `pytest core/tests/test_views_listings.py -v` passes
- `ruff check core/views.py core/tests/test_views_listings.py` passes
- Dashboard page visually shows filtered listings with scores (screenshot in PR)

### Labels
`enhancement` `phase-1` `frontend` `backend`
