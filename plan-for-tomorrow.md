# plan-for-tomorrow.md (tomorrow) — prei

**Horizon**: Tomorrow | **Owner**: Dev lead (Phil) | **Review**: End of session

---

## Single Primary Goal

Triage and begin auth hardening (LIMIT-23): resolve the 10 WARN-level ZAP findings from the authenticated scan.

---

## Target Issues

| Issue | Title | Priority | Status |
|---|---|---|---|
| LIMIT-23 | Authenticated ZAP scan — 10 WARN-level findings | P2 | Open |

### Tasks for tomorrow

1. **Add `SESSION_COOKIE_HTTPONLY` and `SESSION_COOKIE_SECURE`** — resolve Cookie No HttpOnly Flag [10010] and Session ID Transmitted Insecurely [40013]
2. **Add `SECURE_CONTENT_TYPE_NOSNIFF`** — resolve X-Content-Type-Options Header Missing [10021]
3. **Add `X-Frame-Options` or `django-csp`** — resolve CSP Header Not Set [30038] and Permissions Policy Header Not Set [10063]
4. **Add `SECURE_HSTS_SECONDS` + `SECURE_HSTS_INCLUDE_SUBDOMAINS`** — resolve HTTP Only Site [10106]

---

## TDD Execution Protocol

For each task:

1. **Red** — Write a test that asserts the header/cookie is NOT yet set (confirm current state)
2. **Green** — Add the Django setting; confirm the test now passes
3. **Refactor** — Verify no regressions in existing security tests (`tests/test_production_settings.py`)

### Test checklist (per setting)

- [ ] Setting exists in `investor_app/settings.py`
- [ ] Test confirms the setting is enabled when `DEBUG=False`
- [ ] No existing tests break
- [ ] ZAP scan finding is resolved (manual verification if needed)

---

## Retrospective

*To be filled at end of session*

### What went well
-

### What could improve
-

### Backlog deltas
- New items discovered:
- Items to move to P2:
- Items to reject (scope drift):

---

## How This Connects

| Doc | What it answers | Reference |
|---|---|---|
| `EXECUTION_QUEUE.md` | What are the weekly priorities? | ↗ links up |
| `VISION.md` | Why are we building this? | ↗ links up |
| `docs/KNOWN_LIMITATIONS.md` | What is LIMIT-23 and its full context? | parallel |
