## Phase 5.1 — Premium Data Adapters (`core/integrations/premium/`)

### User Story
As an investor subscriber, I want access to premium tax records, zoning data, and land-use classifications so that I can assess regulatory risk before acquiring a property.

### Background
- `core/integrations/sources/attom_adapter.py` already exists (ATTOM API)
- `MarketSnapshot` model exists in `core/models.py`
- No premium data package exists under `core/integrations/premium/`
- Feature flag pattern not yet established

### Acceptance Criteria
- [ ] Create `core/integrations/premium/` package:
  - `__init__.py`
  - `tax_records.py` — `fetch_tax_record(address: str, zip_code: str) -> dict`  
    Placeholder that logs and returns `{"annual_tax": None, "tax_year": None, "status": "not_configured"}` unless `PREMIUM_TAX_API_KEY` is set in env
  - `zoning.py` — `fetch_zoning(address: str, zip_code: str) -> dict`  
    Placeholder returning `{"zone_type": None, "land_use": None, "status": "not_configured"}` unless `PREMIUM_ZONING_API_KEY` is set in env
  - `feature_flags.py` — `is_premium_enabled(feature: str) -> bool`  
    Returns `True` only if the corresponding API key env var is non-empty; reads from `settings`
- [ ] Add to `.env.example`:
  ```
  PREMIUM_TAX_API_KEY=    # leave empty to disable
  PREMIUM_ZONING_API_KEY= # leave empty to disable
  ```
- [ ] Extend `report_listing` view (Phase 2.4) to call premium adapters if enabled and include tax + zoning in the property report template
- [ ] Unit tests in `core/tests/test_premium_adapters.py`:
  - `is_premium_enabled("tax")` with key set → `True`; with key empty → `False`
  - `fetch_tax_record` with key not set → returns dict with `status = "not_configured"`
  - `fetch_tax_record` with key set and mocked HTTP 200 → returns populated dict
  - `fetch_zoning` same patterns as above
  - No unhandled exceptions on any adapter failure

### Files to Change
| File | Action |
|------|--------|
| `core/integrations/premium/__init__.py` | **Create** |
| `core/integrations/premium/tax_records.py` | **Create** |
| `core/integrations/premium/zoning.py` | **Create** |
| `core/integrations/premium/feature_flags.py` | **Create** |
| `.env.example` | **Edit** — add premium keys |
| `core/views.py` | **Edit** — add premium data to `report_listing` context |
| `templates/property_report.html` | **Edit** — add tax/zoning section |
| `core/tests/test_premium_adapters.py` | **Create** |

### Implementation Notes
- Never call live premium APIs in tests — always mock
- Use `settings.PREMIUM_TAX_API_KEY` (loaded via `django-environ`); add to `settings.py` with `env("PREMIUM_TAX_API_KEY", default="")`
- Follow the same error-handling pattern as `core/integrations/market/` adapters

### Definition of Done
- `pytest core/tests/test_premium_adapters.py -v` passes (no live network)
- `ruff check core/integrations/premium/ core/tests/test_premium_adapters.py` passes
- `is_premium_enabled` correctly gates real API calls (verified in tests)

### Labels
`enhancement` `phase-5` `backend` `integration`
