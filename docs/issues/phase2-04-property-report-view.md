## Phase 2.4 — Property Report Detail View

### User Story
As an investor, I want a single-property report page that shows all due diligence data — deal KPIs, neighborhood signals, history, and rent estimates — so that I can make an informed decision without switching tools.

### Background
- `templates/property_report.html` already exists (basic scaffold)
- `report_listing` and `report_property` views exist in `core/views.py`
- `compute_analysis_for_property` exists in `investor_app/finance/utils.py`
- `MarketSnapshot` model and `core/services/market_data.py` (added by Phase 2.2) provide neighborhood data
- `core/services/cma.py` provides `price_per_sqft` and `find_undervalued`

### Acceptance Criteria
- [ ] The `report_listing` view in `core/views.py` renders a complete context dict containing:
  - `listing` — the `Listing` object
  - `score` — `score_listing_v1(listing)` result
  - `ppsf` — price per square foot via `price_per_sqft`
  - `market_snapshot` — nearest `MarketSnapshot` for the listing's `zip_code` (or `None`)
  - `kpis` — dict of `cap_rate`, `cash_on_cash`, `dscr`, `noi` estimated from listing price (use configurable default assumptions from `settings.FINANCE_DEFAULTS`)
- [ ] `templates/property_report.html` displays all context fields in clearly labelled sections:
  - **Listing Details** — address, price, beds/baths, sq_ft, type, posted date
  - **Investment KPIs** — cap rate, CoC, NOI, DSCR
  - **Market Data** — rent index, price trend, crime score, school rating (or "N/A" if no snapshot)
  - **Score** — V1 score with label
- [ ] Add a URL entry in `core/urls.py` for the report page if not already present: `listing/<int:listing_id>/report/`
- [ ] Add integration tests in `core/tests/test_views_listings.py` (or new file):
  - GET `/listing/<id>/report/` returns HTTP 200
  - Context contains `score`, `ppsf`, `kpis` keys
  - Missing `MarketSnapshot` → page still loads (no 500 error)

### Files to Change
| File | Action |
|------|--------|
| `core/views.py` | **Edit** — `report_listing` view: add score, ppsf, market_snapshot, kpis to context |
| `templates/property_report.html` | **Edit** — add all labelled sections |
| `core/urls.py` | **Edit** — verify/add URL for `listing/<id>/report/` |
| `core/tests/test_views_listings.py` | **Edit** — add report view tests |

### Implementation Notes
- Use `settings.FINANCE_DEFAULTS` for default vacancy rate, capex rate, etc.
- Do not call external APIs in the view; use only DB data (`MarketSnapshot`)
- Wrap `compute_analysis_for_property` in `try/except` — return zero KPIs on error
- Use `Decimal` throughout; format in template with `|floatformat:2`

### Definition of Done
- `pytest core/tests/ -k "report" -v` passes
- `ruff check core/views.py templates/` (if applicable) passes
- Property report page renders all sections (screenshot in PR)

### Labels
`enhancement` `phase-2` `frontend` `backend`
