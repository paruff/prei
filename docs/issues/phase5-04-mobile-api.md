## Phase 5.4 — Mobile-Compatible API & Push Notifications

### User Story
As a mobile user, I want to receive push notifications for new high-score listings and view deal details on my phone so that I can act on leads wherever I am.

### Background
- DRF API will be established by Phase 5.3
- `Notification` model exists in `core/models.py`
- `dispatch_alert` exists (or will) in `core/services/alerts.py`
- No push notification service (FCM/APNs) is configured

### Acceptance Criteria
- [ ] Add `device_token` and `platform` (choices: `ios`/`android`/`web`) fields to `NotificationPreference` model in `core/models.py`; create migration
- [ ] Create `core/integrations/push/` package:
  - `__init__.py`
  - `push_adapter.py` — `send_push(device_token: str, platform: str, title: str, body: str) -> bool`  
    Placeholder that logs the notification and returns `True`; add a comment marking the FCM/APNs integration point; reads `PUSH_SERVICE_KEY` from env
- [ ] Update `dispatch_alert` in `core/services/alerts.py` to call `send_push` if:
  - `notification.user.notification_preferences.notify_push is True`
  - `device_token` is set on the preference
- [ ] Add API endpoint `POST /api/devices/register/` — authenticated; accepts `{"device_token": str, "platform": str}`; upserts `NotificationPreference.device_token`
- [ ] Add `PUSH_SERVICE_KEY=` to `.env.example`
- [ ] Unit tests in `core/tests/test_push_notifications.py`:
  - `send_push` logs at INFO level (verified with `caplog`)
  - `send_push` with no `PUSH_SERVICE_KEY` → returns `True` (placeholder, no error)
  - `POST /api/devices/register/` authenticated → 200 and `device_token` saved
  - `POST /api/devices/register/` unauthenticated → 403
  - `dispatch_alert` with `notify_push=True` and `device_token` set → `send_push` called

### Files to Change
| File | Action |
|------|--------|
| `core/models.py` | **Edit** — add `device_token`, `platform` to `NotificationPreference` |
| `core/migrations/` | **Create** — migration |
| `core/integrations/push/__init__.py` | **Create** |
| `core/integrations/push/push_adapter.py` | **Create** |
| `core/services/alerts.py` | **Edit** — wire in push adapter |
| `core/api_views.py` | **Edit** — add `DeviceRegisterView` |
| `core/api_urls.py` | **Edit** — register `POST /api/devices/register/` |
| `.env.example` | **Edit** — add `PUSH_SERVICE_KEY` |
| `core/tests/test_push_notifications.py` | **Create** |

### Implementation Notes
- `send_push` must never raise — always `try/except` and return `False` on error
- `device_token` field: `CharField(max_length=255, blank=True, default="")`
- `platform` field: `CharField(max_length=8, choices=[("ios","iOS"),("android","Android"),("web","Web")], blank=True, default="")`
- `DeviceRegisterView` uses `IsAuthenticated` permission class

### Definition of Done
- `pytest core/tests/test_push_notifications.py -v` passes
- Migration applies and reverses cleanly
- `ruff check core/integrations/push/ core/tests/test_push_notifications.py` passes
- `dispatch_alert` calls `send_push` when appropriate (verified in test with mock)

### Labels
`enhancement` `phase-5` `backend` `mobile`
