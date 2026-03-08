## Phase 4.5 — Production Security Hardening & Audit Trails

### User Story
As an operator, I want the application hardened for production deployment and equipped with an audit trail so that security incidents can be investigated and compliance requirements are met.

### Background
- `investor_app/settings.py` is a single file used for both dev and prod
- `DEBUG=True` is the default — this must never reach production
- No audit log model exists
- No `SECURE_*` Django settings are configured

### Acceptance Criteria
- [ ] Split settings into `investor_app/settings/base.py` and `investor_app/settings/production.py` (or use a `DJANGO_ENV` env var guard in the existing file) with production hardening:
  - `DEBUG = env.bool("DEBUG", default=False)` in production config
  - `SECURE_SSL_REDIRECT = True`
  - `SESSION_COOKIE_SECURE = True`
  - `CSRF_COOKIE_SECURE = True`
  - `SECURE_HSTS_SECONDS = 31536000`
  - `SECURE_CONTENT_TYPE_NOSNIFF = True`
  - `X_FRAME_OPTIONS = "DENY"`
  - `ALLOWED_HOSTS` loaded from `env.list("ALLOWED_HOSTS")`
- [ ] Add an `AuditLog` model to `core/models.py`:
  ```python
  class AuditLog(models.Model):
      user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
      action = models.CharField(max_length=64)   # e.g. "property.created"
      object_type = models.CharField(max_length=64)
      object_id = models.IntegerField(null=True)
      timestamp = models.DateTimeField(auto_now_add=True)
      meta = models.JSONField(default=dict)
  ```
- [ ] Create migration for `AuditLog`
- [ ] Add `core/services/audit.py` with:
  - `log_action(user, action: str, obj=None, meta: dict | None = None) -> AuditLog`
- [ ] Call `log_action` in at least: property creation, listing save, saved search creation
- [ ] Unit tests in `core/tests/test_audit.py` (`@pytest.mark.django_db`):
  - `log_action` creates a record with correct `action`, `object_type`, `object_id`
  - `log_action` with `user=None` → record created with null user (no crash)
  - AuditLog query by `user` and `action` returns correct records

### Files to Change
| File | Action |
|------|--------|
| `investor_app/settings.py` | **Edit** — add production security settings (env-gated) |
| `core/models.py` | **Edit** — add `AuditLog` |
| `core/migrations/` | **Create** — migration |
| `core/services/audit.py` | **Create** |
| `core/tests/test_audit.py` | **Create** |
| `.env.example` | **Edit** — document `DJANGO_ENV`, `SECURE_*` vars |

### Implementation Notes
- Never hardcode `SECRET_KEY`; confirm it reads from `env("SECRET_KEY")` with no default
- Add `DJANGO_ENV=production` to `.env.example` with a comment
- `AuditLog` must be `Meta: ordering = ["-timestamp"]`
- `log_action` is synchronous; do not use Celery for audit writes (guarantees consistency)

### Definition of Done
- `pytest core/tests/test_audit.py -v` passes
- `ruff check core/services/audit.py core/models.py investor_app/settings.py` passes
- Django `check --deploy` passes with no critical issues (run `python manage.py check --deploy` in CI)
- Migration applies and reverses cleanly

### Labels
`security` `phase-4` `backend`
