## Phase 1.5 — Alerts Service (`core/services/alerts.py`)

### User Story
As an investor, I want to be notified when a new listing matches my saved search criteria and score threshold so that I can act quickly on good deals.

### Background
- `SavedSearch` model exists in `core/models.py` with fields: `user`, `name`, `query`, `zip_code`, `state`, `min_price`, `max_price`
- `Listing` model exists in `core/models.py`
- `NotificationPreference` and `Notification` models exist in `core/models.py`
- `score_listing_v1` exists in `investor_app/finance/utils.py`
- Celery + Redis are configured in `docker-compose.yml` and `investor_app/celery.py`
- `FINANCE_DEFAULTS` in `investor_app/settings.py` can store a default score threshold

### Acceptance Criteria
- [ ] Create `core/services/alerts.py` with:
  - `evaluate_listing_alerts(listing: Listing) -> list[Notification]`  
    — query all active `SavedSearch` objects, apply filter criteria, compute `score_listing_v1`, compare against threshold from `settings.FINANCE_DEFAULTS["alert_score_threshold"]` (default `5.0`), create and return `Notification` objects (do **not** send yet)
  - `dispatch_alert(notification: Notification) -> None`  
    — placeholder that logs the notification via Python `logging`; later will send email/SMS
- [ ] Add `"alert_score_threshold": Decimal("5.0")` to `FINANCE_DEFAULTS` in `investor_app/settings.py`
- [ ] Add a Celery task in `core/tasks.py`:  
  `check_new_listing_alerts(listing_id: int)` — loads the listing, calls `evaluate_listing_alerts`, calls `dispatch_alert` for each result
- [ ] Unit tests in `core/tests/test_alerts.py`:
  - listing that matches a saved search above threshold → notification created
  - listing that matches filter but score below threshold → no notification
  - listing that does not match saved search filters → no notification
  - `dispatch_alert` logs at INFO level (use `caplog` fixture)

### Files to Change
| File | Action |
|------|--------|
| `core/services/alerts.py` | **Create** |
| `core/tasks.py` | **Edit** — add `check_new_listing_alerts` Celery task |
| `investor_app/settings.py` | **Edit** — add `alert_score_threshold` to `FINANCE_DEFAULTS` |
| `core/tests/test_alerts.py` | **Create** |

### Implementation Notes
- Use `Decimal` throughout; never `float` for threshold comparisons
- Do **not** import from `core.views`; services are view-agnostic
- Use `logging.getLogger(__name__)` for structured logs
- Guard against `SavedSearch.DoesNotExist` gracefully
- Follow Google-style docstrings and type hints on all public functions

### Definition of Done
- `pytest core/tests/test_alerts.py -q` passes
- `ruff check core/services/alerts.py core/tests/test_alerts.py` passes
- `dispatch_alert` emits a log line at `INFO` level (verified with `caplog`)

### Labels
`enhancement` `phase-1` `backend`
