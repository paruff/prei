# prei — Passive Real Estate Investment Analytics

A Django-based web application for **personal passive real estate investors** — buy-and-hold investors who want to analyze single-family rentals, small multifamily properties, and BRRRR deals with professional-grade underwriting. No fluff, no auction monitoring, no market timing — just durable cash-flow analysis.

## 📊 Status

**Latest release:** `v0.4.0` (development milestone)

### What works now
- **Deal pipeline** — Screen, offer, renovate, close, and lease properties through a visual pipeline workflow with 9-criteria screening
- **Discovery source models** — Structured ingestion for HUD REO (ArcGIS Hub), USDA REO, Dallas County NTS, and ATTOM preforeclosure notices
- **Pipeline screening** — Hard-kill and yield scoring for HUD/USDA/county sources; "Add to Pipeline" flow from list/detail views
- **Growth area explorer** — Discover and compare markets by demographic and economic indicators with pagination and CSV export
- **VRM foreclosures** — Foreclosure listings with direct linking to pipeline discovery
- **Property underwriting** — Full scorecard (CoC, Cap Rate, DSCR, GRM), BRRRR calculator, hold projections, tax modeling
- **Market intelligence** — Price-to-rent ratio, population growth, employment diversity, school ratings, walk scores
- **Auto-versioned releases** — Git tags → Docker bake → structured logging; every build carries its version
- **Python 3.14 + Django 6.0** — Fully migrated to latest stable runtimes

### What's next
- County foreclosure notice scraper framework (additional counties)
- Property comparison and portfolio scenario modeling
- Enhanced notifications and collaboration features
- Additional data source integrations (Redfin, Zillow)

---

## ✨ Features

- **Deal Screener Dashboard** — At-a-glance KPI grid (CoC, Cap Rate, DSCR, GRM, Score) with color-coded verdicts
- **Property Entry Form** — Clean, responsive form with styled inputs, smart grids, and real-time validation
- **Property Detail Scorecard** — Full underwriting score breakdown with pass/fail flags, verdict badge, color-coded metrics
- **BRRRR Calculator** — Client-side calculator with zero-ARV guard, verdict banner, DSCR warning, locale-formatted numbers
- **Markets Page** — Price-to-rent ratio, population growth, employment diversity, overall market score per ZIP
- **Underwriting Score v2** — Multi-signal scoring (1% Rule, CoC, DSCR, Cap Rate, GRM, After-Tax CoC) with verdict
- **Investment Analysis** — Financial KPIs (Cash-on-Cash, Cap Rate, NOI, IRR, DSCR)
- **Hold Period Projections** — Year-by-year rent growth, equity build-up, appreciation scenarios, net sale proceeds
- **Depreciation & Tax Modeling** — 27.5-year straight-line depreciation and after-tax cash flow

## Custom UX/UI Design System (No Bootstrap)

Built on a bespoke design system — zero Bootstrap or third-party CSS frameworks:

| Token | Purpose |
|---|---|
| `--font-sans` / `--font-mono` | Typography stack |
| `--color-primary` / `--color-grow-*` | Semantic palette (action, success, caution, risk) |
| `--color-verdict-*` | Underwriting verdict colors (A/B/C/moderate) |
| `--surface-page` / `--surface-card` / `--surface-secondary` | Surface hierarchy |
| `--radius-sm` / `--radius-md` / `--radius-lg` / `--radius-pill` | Corner rounding |
| `--sp-1` through `--sp-8` | Spacing scale (4 px increments) |
| `--text-xs` / `--text-sm` / `--text-base` / `--text-lg` / `--text-xl` | Type scale |
| `--border-default` / `--border-subtle` | Border weights |

**Components:** `.card`, `.kpi-grid`, `.data-table`, `.verdict-badge`, `.score-bar`, `.tab-bar`, `.layout-2col`, `.page-header`, `.filter-bar`, `.chip`, `.btn`, `.btn-primary`, `.form-input`, `.form-grid-2/3/2-1/2-1-1`, `.empty-state`, `.flag-list`, `.message`, `.brrrr-banner`, `.result-emphasis`, `.form-divider`, `.form-subsection-label`

---

## Quick Start — Choose Your Environment

| Environment | Name | Best For | Database | Start Command |
|---|---|---|---|---|
| **local** | **dev** | Daily development on your machine | SQLite (`db.sqlite3`) | `docker compose up -d` |
| **devcontainer** | **test** | GitHub Codespaces / VS Code Dev Container | SQLite (`/home/vscode/db.sqlite3`) | Open in Codespace → `make dev` |
| **render** | **prod** | Production deployment | PostgreSQL (managed) | Click "Deploy to Render" button |

### Local Development (dev)

```bash
git clone https://github.com/paruff/prei.git
cd prei
cp .env.example .env
# Edit .env — set SECRET_KEY, DJANGO_ENV=development
docker compose up -d
# Open http://127.0.0.1:8000
# Login: demo@prei.dev / DemoPass123!
```

> `docker compose up -d` automatically runs migrations and seeds the demo user — no extra steps.
> **Windows users:** See [Local Docker Setup Guide](docs/how-to-guides/local-dev.md) for WSL2/memory config.

### Dev Container / Codespaces (test)

1. Open repo in **GitHub Codespaces** (Code → Codespaces → Create codespace on main)
   **or** VS Code Dev Containers (Reopen in Container)
2. Wait for build (~2 min), then run in terminal:
   ```bash
   make dev
   ```
   > `make dev` runs `migrate` and `seed_data` automatically — the demo user will be created for you.
3. Open forwarded port 8000 → `http://localhost:8000`

**Demo login:** `demo@prei.dev` / `DemoPass123!`

### Deploy to Render (prod)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/paruff/prei)

The `render.yaml` blueprint provisions:
- `prei-web` — Django app via Gunicorn
- `prei-db` — Managed PostgreSQL

**Required env vars in Render dashboard:**
- `SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`
- `ALLOWED_HOSTS` — your Render URL, e.g. `your-app.onrender.com`

---

## API Keys for Data-Driven Decisions

| Key | Purpose | Get Key | Required For |
|---|---|---|---|
| `ATTOM_API_KEY` | Property details, comps, foreclosures | [api.attomdata.com](https://api.attomdata.com) | Comps, property enrichment |
| `CENSUS_API_KEY` | ZIP demographics, population, income | [api.census.gov](https://api.census.gov/data/key_signup.html) | Market scoring |
| `BLS_API_KEY` | State/metro unemployment, wages | [data.bls.gov/registrationEngine](https://data.bls.gov/registrationEngine/) | Market scoring |
| `RENTCAST_API_KEY` | Rental estimate comps | [rentcast.io](https://rentcast.io) | Rent estimates |
| `GREATSCHOOLS_API_KEY` | School ratings | [greatschools.org/api](https://www.greatschools.org/api/) | Neighborhood quality |
| `WALKSCORE_API_KEY` | Walkability scores | [walkscore.com/professional/api](https://www.walkscore.com/professional/api) | Neighborhood quality |

Add keys to `.env` (local/dev) or Render dashboard (prod). See [API Keys Reference](docs/reference/api-keys.md) for details.

---

## Documentation

Full documentation at **[https://paruff.github.io/prei/](https://paruff.github.io/prei/)** (Diátaxis framework):

- **Tutorials** — [Getting Started](https://paruff.github.io/prei/tutorials/getting-started/)
- **How-to Guides** — [Local Dev](docs/how-to-guides/local-dev.md) · [Dev Container](docs/how-to-guides/devcontainer.md) · [Render Deploy](docs/how-to-guides/render-deploy.md)
- **Reference** — [Financial KPIs](docs/reference/financial-kpis.md) · [Data Sources](docs/reference/data-sources.md) · [API Keys](docs/reference/api-keys.md)
- **Explanation** — [Architecture](docs/explanation/architecture.md) · [Design System](docs/explanation/design-system.md)

Build locally:
```bash
pip install -r docs-requirements.txt
mkdocs serve
```

---

## CI & Tooling

- **Lint/Format:** ruff
- **Type Check:** mypy
- **Tests:** pytest + Makefile validation (no duplicate targets, proper syntax)
- **Docs:** MkDocs Material
- **CI:** GitHub Actions (`.github/workflows/`) — DORA-friendly logging

---

## Repository Purpose

Host the web application and all related code, tests, infra config, and documentation for **passive residential real estate investment** analytics — buy-and-hold SFR/small multifamily, BRRRR, and market intelligence.

## License

Licensed per repository terms.
