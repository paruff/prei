## Phase 5.3 — DRF REST API for Listings & Analytics

### User Story
As a third-party developer or mobile app, I want a documented REST API for listings and deal analytics so that I can build integrations without scraping the HTML.

### Background
- `core/api_views.py` and `core/api_urls.py` exist with several DRF endpoints already
- `core/serializers.py` exists
- `Listing` serializer and list/detail endpoints do **not** yet exist
- Rate limiting is not configured

### Acceptance Criteria
- [ ] Add to `core/serializers.py`:
  - `ListingSerializer` — all `Listing` fields plus a computed `score` field (read-only, from `score_listing_v1`)
  - `MarketSnapshotSerializer` — all `MarketSnapshot` fields
- [ ] Add to `core/api_views.py`:
  - `ListingListView` (`ListAPIView`) — supports filter params: `state`, `min_price`, `max_price`, `property_type`, `beds`; results ordered by `score` descending; pagination (page size 20)
  - `ListingDetailView` (`RetrieveAPIView`) — returns single listing with score and nearest `MarketSnapshot`
  - `PortfolioAnalyticsView` — authenticated endpoint returning `aggregate_portfolio(request.user)` as JSON
- [ ] Register URLs in `core/api_urls.py`:
  - `GET /api/listings/` → `ListingListView`
  - `GET /api/listings/<id>/` → `ListingDetailView`
  - `GET /api/portfolio/analytics/` → `PortfolioAnalyticsView`
- [ ] Add DRF throttling in `investor_app/settings.py`:
  - `AnonRateThrottle`: 100/day
  - `UserRateThrottle`: 1000/day
- [ ] API tests in `core/tests/test_api_listings.py`:
  - `GET /api/listings/` returns 200 and a list with `score` field
  - Filter by `state` returns only matching listings
  - `GET /api/listings/<id>/` returns 200 with correct listing and `market_snapshot` key
  - `GET /api/portfolio/analytics/` unauthenticated → 403
  - `GET /api/portfolio/analytics/` authenticated → 200 with `total_noi`, `avg_cap_rate`, `avg_coc`

### Files to Change
| File | Action |
|------|--------|
| `core/serializers.py` | **Edit** — add `ListingSerializer`, `MarketSnapshotSerializer` |
| `core/api_views.py` | **Edit** — add `ListingListView`, `ListingDetailView`, `PortfolioAnalyticsView` |
| `core/api_urls.py` | **Edit** — register new URLs |
| `investor_app/settings.py` | **Edit** — add DRF `DEFAULT_THROTTLE_CLASSES` and `DEFAULT_THROTTLE_RATES` |
| `core/tests/test_api_listings.py` | **Create** |

### Implementation Notes
- `score` is a `SerializerMethodField`; it calls `score_listing_v1` — wrap in `try/except` returning `None` on failure
- Use DRF's `PageNumberPagination` with `page_size = 20`
- `PortfolioAnalyticsView` uses `IsAuthenticated` permission class
- DRF is already in `requirements.txt` — do not add a new dependency

### Definition of Done
- `pytest core/tests/test_api_listings.py -v` passes
- `ruff check core/api_views.py core/serializers.py` passes
- `/api/listings/` returns paginated JSON with `score` (verified in test)

### Labels
`enhancement` `phase-5` `backend` `api`
