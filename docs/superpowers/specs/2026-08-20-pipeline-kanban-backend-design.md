# Pipeline Kanban Backend — Phase 2 Design

**Date**: 2026-08-20
**Status**: Approved for implementation
**Audit reference**: docs/assessments/PRODUCT_AUDIT_2026-08-19.md (Phase 2, Week 2)

---

## 1. Problem Statement

The kanban frontend (`templates/pipeline/kanban.html`) has full drag-and-drop markup and JS but only supports stage advancement via POST to `/pipeline/kanban/`. The audit identifies missing RESTful endpoints for granular actions: `advance`, `kill`, `hold`, `reactivate`. This design adds those endpoints and wires up UI controls on each kanban card.

---

## 2. Architecture

### 2.1 New Endpoints (added to `core/views/__init__.py`)

| Endpoint | Method | Service Function | Response |
|----------|--------|------------------|----------|
| `/pipeline/<pk>/advance/` | POST | `advance_stage()` | JSON `{status: "ok", stage: "..."}` |
| `/pipeline/<pk>/kill/` | POST | `kill_property()` | JSON `{status: "ok"}` |
| `/pipeline/<pk>/hold/` | POST | `hold_property()` | JSON `{status: "ok"}` |
| `/pipeline/<pk>/reactivate/` | POST | `reactivate_property()` | JSON `{status: "ok"}` |

All endpoints:
- Require authentication (`@login_required`)
- Validate ownership (`user=request.user`)
- Return JSON for fetch API consumption
- Include CSRF protection (Django's default)

### 2.2 Existing Endpoint (unchanged)

`/pipeline/kanban/` POST — drag-drop stage jump (any stage). Stays for drag-and-drop flexibility.

### 2.3 URL Registration (`core/urls.py`)

Add 4 new path entries with `pipeline_` prefix.

---

## 3. Frontend Changes (`templates/pipeline/kanban.html`)

### 3.1 Card Action Menu

Add a dropdown on each `.kanban-card` with context-aware actions:
- **Always**: Kill, Hold
- **When status=KILLED or ON_HOLD**: Reactivate

### 3.2 Action Handlers

Each action:
1. Sends `fetch` POST to corresponding endpoint with CSRF token
2. On success: Kill/Hold → fade out + remove card; Reactivate → reload page (or fetch updated board)
3. On error: Show toast/alert with server message

---

## 4. E2E Tests (new files in `tests/e2e/`)

| Test File | Coverage |
|-----------|----------|
| `test_kanban_advance_endpoint.py` | `/advance/` endpoint — sequential stage advance, boundary (STABILIZED), permissions |
| `test_kanban_kill_hold_reactivate.py` | Kill/hold/reactivate endpoints + UI interactions |
| Extended `test_kanban_e2e.py` | Integration: drag-drop + new actions in same session |

---

## 5. Out of Scope (Deferred)

- WebSocket / polling for real-time multi-user updates
- Server-sent events (SSE)
- Optimistic UI with conflict resolution

---

## 6. Acceptance Criteria

1. All 4 new endpoints return 200 JSON on success, 400/404 on error
2. Kanban card dropdown shows correct actions per status
3. Kill → card removed from board; Hold → card removed; Reactivate → card reappears
4. E2E tests pass for all endpoints + UI flows
5. Existing kanban drag-drop continues to work

---

## 7. Dependencies

- Existing service functions: `advance_stage`, `kill_property`, `hold_property`, `reactivate_property` (all tested)
- Existing `PipelineProperty` model with `Stage` and `Status` TextChoices
- Existing `pipeline_kanban` view and template (JS fetch pattern established)
