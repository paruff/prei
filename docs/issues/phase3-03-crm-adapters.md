## Phase 3.4 — CRM Workflow Adapters (`core/integrations/crm/`)

### User Story
As an investor, I want deal alerts and property reports to be forwarded to my CRM (via webhook), email, or calendar so that my investment pipeline stays in sync automatically.

### Background
- `dispatch_alert` placeholder exists (or will be added) in `core/services/alerts.py` (Phase 1.5)
- `Notification` model exists in `core/models.py`
- `NotificationPreference` model exists in `core/models.py` with `notify_email`, `notify_sms`, `notify_in_app`
- No CRM/webhook integration exists today

### Acceptance Criteria
- [ ] Create `core/integrations/crm/` package with:
  - `__init__.py`
  - `webhook.py` — `send_webhook(url: str, payload: dict) -> bool`  
    Posts JSON payload to `url`; returns `True` on HTTP 2xx, `False` otherwise; logs on failure
  - `email_adapter.py` — `send_email_notification(notification: Notification) -> bool`  
    Uses Django's `send_mail`; reads `to_address` from `notification.user.notificationpreferences.email_address`; returns `True` on success; placeholder when `EMAIL_HOST` not configured
  - `calendar_adapter.py` — `create_calendar_event(title: str, date, description: str) -> dict`  
    Placeholder returning `{"status": "queued", "title": title}`; logs the event; ready for Google Calendar / iCal integration
- [ ] Add `WEBHOOK_ALERT_URL` to `.env.example` (empty default)
- [ ] Update `dispatch_alert` in `core/services/alerts.py` to:
  - Call `send_email_notification` if `notify_email` is True
  - Call `send_webhook` if `settings.WEBHOOK_ALERT_URL` is set
- [ ] Unit tests in `core/tests/test_crm_adapters.py`:
  - `send_webhook` with mocked `requests.post` returning 200 → returns `True`
  - `send_webhook` with mocked `requests.post` raising `ConnectionError` → returns `False`, logs ERROR
  - `send_email_notification` with mock → `send_mail` called with correct args
  - `send_email_notification` when `EMAIL_HOST` not set → returns `False` without raising
  - `create_calendar_event` → returns dict with `status` key

### Files to Change
| File | Action |
|------|--------|
| `core/integrations/crm/__init__.py` | **Create** |
| `core/integrations/crm/webhook.py` | **Create** |
| `core/integrations/crm/email_adapter.py` | **Create** |
| `core/integrations/crm/calendar_adapter.py` | **Create** |
| `core/services/alerts.py` | **Edit** — wire in CRM adapters |
| `.env.example` | **Edit** — add `WEBHOOK_ALERT_URL` |
| `core/tests/test_crm_adapters.py` | **Create** |

### Implementation Notes
- `requests` library is already in `requirements.txt` (verify before importing)
- All adapters must be independently importable — no circular imports
- Never raise unhandled exceptions from adapters; always catch and log
- Type hints and Google-style docstrings required

### Definition of Done
- `pytest core/tests/test_crm_adapters.py -v` passes (all mocked, no live network)
- `ruff check core/integrations/crm/ core/tests/test_crm_adapters.py` passes
- `WEBHOOK_ALERT_URL` documented in `.env.example`

### Labels
`enhancement` `phase-3` `backend` `integration`
