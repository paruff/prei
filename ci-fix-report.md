Changed:      docker-compose.yml:16 — DATABASE_URL moved from /app/db.sqlite3 to
              /app/.runtime/db.sqlite3
              .env:47 — reverted (no change needed; devcontainer.json handles
              Codespaces ALLOWED_HOSTS)
Validation:   docker compose up — migrations applied successfully (all 22
              migrations), gunicorn started on 0.0.0.0:8000, 2 workers booted
              Health: PASS
              Warnings: No directory at: /app/staticfiles/ (non-fatal,
              collectstatic not run in dev)

              Previously failing: sqlite3.OperationalError unable to open
              database file → crash loop
              Now: PASSING

Remaining Risks:
  - 401 from Codespaces port URL: NOT a Django issue. Caused by Codespaces
    port visibility set to "Private" (GitHub OAuth gate). Fix: Ports tab →
    port 8000 → right-click → "Port Visibility" → "Public".
  - Static files warning: run `python manage.py collectstatic --noinput` to
    resolve (harmless in dev, needed before production deployment).
  - No demo user created: run `docker compose exec web python manage.py
    seed_data` to create demo@prei.dev / DemoPass123!

Root Cause Category: Infrastructure

Note: .devcontainer/devcontainer.json already has ALLOWED_HOSTS=* for
Codespaces. The 401 is not from Django's ALLOWED_HOSTS check (which would
return 400). The 401 is GitHub's OAuth gate on private port forwarding.

Cleanup:
  Deleted railway.toml and fly.toml — these deployment configs are for
  providers not in the chosen three environments (local/dev, devcontainer/test,
  render/prod). Removed Fly.io reference from SECURITY.md:227.
