# Deploy to Render (prod environment)

This guide covers production deployment to **Render** using the `render.yaml` blueprint.

---

## One-Click Deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/paruff/prei)

Click the button → connect your GitHub account → select this repository → Render provisions everything.

---

## What Gets Created

| Resource | Name | Type |
|---|---|---|
| Web Service | `prei-web` | Python (Dockerfile) |
| Database | `prei-db` | Managed PostgreSQL 16 |

**Web service config** (from `render.yaml`):
- Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- Pre-deploy: `python manage.py migrate --noinput`
- Start: `gunicorn investor_app.wsgi:application --bind 0.0.0.0:$PORT --workers 2`
- Health check: `GET /health/` → `{"status": "ok"}`
- Env: `DJANGO_ENV=production`, `DEBUG=False`

---

## Required Environment Variables

Set these in **Render Dashboard → Environment** before first deploy:

| Variable | Value | Notes |
|---|---|---|
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(50))"` | **Required** — generate a secure random value |
| `ALLOWED_HOSTS` | `your-app.onrender.com` | Comma-separated, no spaces. Your Render subdomain. |

**Optional (for external data features):**
| Variable | Purpose |
|---|---|
| `ATTOM_API_KEY` | Property/comps data |
| `CENSUS_API_KEY` | Demographics |
| `BLS_API_KEY` | Employment data |
| `RENTCAST_API_KEY` | Rental estimates |
| `GREATSCHOOLS_API_KEY` | School ratings |
| `WALKSCORE_API_KEY` | Walkability |

---

## Database

- **PostgreSQL** (managed by Render)
- Connection string injected via `DATABASE_URL` from `prei-db` resource
- Migrations run automatically on each deploy (`preDeployCommand`)
- Backups: Render provides daily automated backups (7-day retention on free tier)

---

## Static Files

- Collected during build: `python manage.py collectstatic --noinput`
- Served by WhiteNoise (configured in `settings.py`)
- No separate CDN needed for typical usage

---

## Custom Domain (Optional)

1. Render Dashboard → `prei-web` → **Settings → Custom Domains**
2. Add your domain (e.g., `app.yourdomain.com`)
3. Update DNS: CNAME → `your-app.onrender.com`
4. Update `ALLOWED_HOSTS` in Render env vars to include your custom domain
5. Render provisions TLS automatically (Let's Encrypt)

---

## Deploy Pipeline

```
git push origin main
    │
    ▼
GitHub Actions: ci-quality.yml (lint, typecheck, test)
    │
    ▼
Render auto-deploys on push to main
    │
    ├── Build image (Dockerfile)
    ├── Run collectstatic
    ├── Run migrations (preDeployCommand)
    ├── Start gunicorn
    └── Health check /health/
```

---

## Verify Deployment

```bash
# Health check
curl https://your-app.onrender.com/api/health/
# → {"status": "ok"}

# Home page
curl -I https://your-app.onrender.com/
# → 200 OK
```

---

## Troubleshooting

### Build fails
- Check Render build logs
- Common: missing `SECRET_KEY` or `ALLOWED_HOSTS` in env vars
- Python version mismatch: `render.yaml` uses base image from Dockerfile (3.14)

### Migrations fail
- Check "Pre-deploy" logs in Render
- Ensure `DATABASE_URL` is injected (automatic from `prei-db`)

### 502 Bad Gateway
- Check "Deploy" logs for gunicorn startup errors
- Verify `PORT` env var is used (Render sets it automatically)

### Static files 404
- Ensure `collectstatic` ran in build (check build logs)
- WhiteNoise serves from `STATIC_ROOT` — verify `STATIC_URL` matches

---

## Rollback

Render Dashboard → `prei-web` → **Deployments** → click previous successful deploy → **Rollback to this deploy**.

---

## Cost Estimate (2025)

| Resource | Free Tier | Paid |
|---|---|---|
| Web Service | 750 hrs/mo, 512 MB RAM | $7/mo for 1 GB |
| PostgreSQL | 90 days, 1 GB storage | $7/mo for 1 GB |

Free tier is sufficient for evaluation and light production use.
