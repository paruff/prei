## Phase 3.3 — Recommendations Service (`core/services/recommendations.py`)

### User Story
As an investor, I want personalised listing recommendations based on my saved searches and previously viewed/saved deals so that I discover opportunities I would have otherwise missed.

### Background
- `SavedSearch` model: `user`, `zip_code`, `state`, `min_price`, `max_price`, `query`
- `Listing` model: full listing data
- `UserWatchlist` model: user's saved foreclosure properties (can be extended or mirrored)
- `rank_listings` will be available from Phase 3.2

### Acceptance Criteria
- [ ] Create `core/services/recommendations.py` with:
  - `recommend_listings(user, limit: int = 10) -> list[dict]`  
    — loads user's `SavedSearch` objects, unions the filtered listing querysets, deduplicates by `listing.id`, calls `rank_listings`, and returns the top `limit` entries
  - `explain_recommendation(listing: Listing, saved_search: SavedSearch) -> str`  
    — returns a human-readable string like `"Matches your search 'Downtown Flips': $150k in AZ with 3+ beds"`
- [ ] Unit tests in `core/tests/test_recommendations.py` using `@pytest.mark.django_db`:
  - User with no saved searches → returns empty list
  - User with one saved search matching two listings → returns both, sorted by composite score
  - Listings that match multiple saved searches → deduplicated (appear only once)
  - `limit` parameter is respected
  - `explain_recommendation` returns a non-empty string containing the search name
- [ ] Add a `recommendations` section to `templates/dashboard.html` (top 5 listings) and pass context from `dashboard` view

### Files to Change
| File | Action |
|------|--------|
| `core/services/recommendations.py` | **Create** |
| `core/tests/test_recommendations.py` | **Create** |
| `core/views.py` | **Edit** — add `recommendations` to `dashboard` context |
| `templates/dashboard.html` | **Edit** — add recommendations section |

### Implementation Notes
- Do not call external APIs; use only DB data
- Depend on Phase 3.2 (`rank_listings`) being available; if not merged yet, call `score_listing_v1` directly as fallback
- Use `Listing.objects.filter(...)` for each saved search; union with `|` operator or `Q` objects
- All business logic in the service; view only calls the service and passes result to template

### Definition of Done
- `pytest core/tests/test_recommendations.py -v` passes
- `ruff check core/services/recommendations.py core/tests/test_recommendations.py` passes
- Dashboard shows recommendations section (screenshot in PR)

### Labels
`enhancement` `phase-3` `backend` `frontend`
