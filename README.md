# prei — Passive Real Estate Investment Analytics

A Django-based web application for **personal passive real estate investors** — buy-and-hold
investors who want to analyze single-family rentals, small multifamily properties, and BRRRR
deals with professional-grade underwriting. No fluff, no auction monitoring, no market timing —
just durable cash-flow analysis.

## ✨ Features

- **Deal Screener Dashboard** — At-a-glance KPI grid (CoC, Cap Rate, DSCR, GRM, Score) with
  color-coded verdicts for every property in your portfolio
- **Property Entry Form** — Clean, responsive form with styled inputs, smart grids, and
  real-time validation
- **Property Detail Scorecard** — Full underwriting score breakdown with pass/fail flags,
  verdict badge, and color-coded metrics
- **BRRRR Calculator** — Fully client-side calculator with zero-ARV guard, verdict banner
  (Full Cycle / Partial Recycle / Capital Trap), DSCR warning, and locale-formatted numbers
- **Markets Page** — Price-to-rent ratio, population growth, employment diversity, and
  overall market score per ZIP code; refresh scoped to your properties
- **Underwriting Score v2** — Multi-signal scoring (1% Rule, CoC, DSCR, Cap Rate, GRM,
  After-Tax CoC) with "Strong Buy" / "Conditional" / "Pass" verdict
- **Investment Analysis** — Calculate financial KPIs (Cash-on-Cash, Cap Rate, NOI, IRR, DSCR)
- **Hold Period Projections** — Year-by-year rent growth, equity build-up, appreciation
  scenarios, and net sale proceeds
- **Depreciation & Tax Modeling** — 27.5-year straight-line depreciation and after-tax cash
  flow calculations
- **Investment Targets** — Personalised target thresholds (min CoC, min DSCR, max GRM,
  target hold years) that drive scoring

## Custom UX/UI Design System (No Bootstrap)

The entire UI is built on a bespoke design system — zero Bootstrap or third-party CSS frameworks:

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

**Components:** `.card`, `.kpi-grid`, `.data-table`, `.verdict-badge`, `.score-bar`, `.tab-bar`,
`.layout-2col`, `.page-header`, `.filter-bar`, `.chip`, `.btn`, `.btn-primary`, `.form-input`,
`.form-grid-2`/`3`/`2-1`/`2-1-1`, `.empty-state`, `.flag-list`, `.message`, `.brrrr-banner`,
`.result-emphasis`, `.form-divider`, `.form-subsection-label`

**Key rules:**
- Widget base classes (`StyledNumberInput`, `StyledTextInput`, `StyledSelect`) auto-apply CSS
  classes — no per-field `attrs` in templates
- Color classes come from Python properties (`score.coc_color_class`) — no threshold comparisons
  in templates
- Tab switching uses `panel.hidden` — not `style.display`
- No inline `style=` on layout elements (exceptions: `table.style.opacity` in JS, `width:score%`
  in score bars, and PDF export inline styles)
- No `!important` in CSS
- Fully responsive: 4-column → 2-column → 1-column KPI grid at 640px / 400px breakpoints

## 🚀 Quick Start

Choose the path that fits your situation:

| Path | Best for | Guide |
|---|---|---|
| **Docker (local)** | Running the app locally on Windows/Mac | [Docker Local Setup](docs/how-to-guides/docker-local-setup.md) |
| **GitHub Codespaces** | Zero-install, browser-based evaluation | [Getting Started Tutorial](https://paruff.github.io/prei/tutorials/getting-started/) |
| **Dev Container** | Local VS Code development | See Dev Container section below |

> ⚠️ **Windows + Docker users:** Read the [Docker Local Setup guide](docs/how-to-guides/docker-local-setup.md)
> before editing `.env` — several defaults are production-only and will prevent the app
> from loading in a browser without changes.

## Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/paruff/prei)

This repository includes a root `render.yaml` blueprint that provisions:

- `prei-web` (Django app via Gunicorn)
- `prei-db` (managed PostgreSQL)

Steps:

1. Click the deploy button above and select this repository.
2. In Render, set required environment variables when prompted:
   - `SECRET_KEY`
   - `ALLOWED_HOSTS` (comma-separated, for example `your-app.onrender.com`)
3. Deploy the blueprint.

Notes:
- Static assets are collected during build (`python manage.py collectstatic --noinput`).
- Database migrations run before each web deploy (`python manage.py migrate --noinput`).
- The web service health check uses `GET /health/` and returns `{"status": "ok"}`.
- Production mode is enforced with `DJANGO_ENV=production` and `DEBUG=False`.

### Fastest path: GitHub Codespaces

No installation required. Open the repo in a Codespace and the full environment
starts automatically:

1. Click **Code → Codespaces → Create codespace on main**
2. Wait for the environment to build (~2 minutes)
3. Run `make dev` in the integrated terminal
4. Open the forwarded port for `8000`

Demo login:
- **Email:** `demo@prei.dev`
- **Password:** `DemoPass123!`

### Local Docker (Windows 11)

See the full **[Docker Local Setup guide](docs/how-to-guides/docker-local-setup.md)**
for Windows environment prep, WSL2 configuration, and browser troubleshooting.

Quick summary once your environment is ready:

```powershell
git clone https://github.com/paruff/prei.git
cd prei
copy .env.example .env
# Edit .env — see guide for required changes
docker compose up -d
```

Then open `http://127.0.0.1:8000` in your browser.

## 📚 Documentation

Comprehensive documentation is available at **[https://paruff.github.io/prei/](https://paruff.github.io/prei/)**

The documentation follows the [Diátaxis framework](https://diataxis.fr/) with four sections:
- **[Tutorials](https://paruff.github.io/prei/tutorials/getting-started/)** — Step-by-step learning guides
- **[How-to Guides](https://paruff.github.io/prei/how-to-guides/)** — Practical solutions for specific tasks
- **[Reference](https://paruff.github.io/prei/reference/)** — Technical specifications and API docs
- **[Explanation](https://paruff.github.io/prei/explanation/)** — Architecture and design rationale

To build documentation locally:
```bash
pip install -r docs-requirements.txt
mkdocs serve  # View at http://127.0.0.1:8000
```

## Quick start (local)

For detailed setup instructions, see the **[Getting Started Tutorial](https://paruff.github.io/prei/tutorials/getting-started/)**.

1. Clone the repo:
   - `git clone git@github.com:paruff/prei.git`
   - `cd prei`

2. Create a virtual environment and install deps:
   - `python3.11 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`

3. Create .env from .env.example and update values:
   - `cp .env.example .env`
   - Edit `.env` (set SECRET_KEY, DATABASE_URL)

4. Run migrations and start dev server:
   - `python manage.py migrate`
   - `python manage.py seed_data`
   - `python manage.py runserver`

   Seed command creates a demo superuser and sample properties:
   - Email: `demo@prei.dev`
   - Password: `DemoPass123!`
   - Re-run safely: `python manage.py seed_data`
   - Reset + reseed: `python manage.py seed_data --reset`
   - For non-local environments, only run this command with explicit non-default `SEED_DEMO_EMAIL` and `SEED_DEMO_PASSWORD`.

## Quick start (Codespaces / Dev Container)

If you open this repository in a GitHub Codespace or VS Code Dev Container, use the devcontainer as the development runtime instead of trying to run Docker Compose inside the container.

1. Open the repository in the devcontainer.
   - The devcontainer starts `web` and `db` from [.devcontainer/docker-compose.yml](./.devcontainer/docker-compose.yml).
   - Dependencies are installed automatically by [.devcontainer/devcontainer.json](./.devcontainer/devcontainer.json).

2. Initialize the app in the integrated terminal:
   - `make dev`

   In a second terminal, create a superuser the first time only:
   - `python manage.py createsuperuser`

3. Open the forwarded port for `8000`.
   - Web: `http://localhost:8000`
   - Admin: `http://localhost:8000/admin`

This is the fastest workflow for rapid development because the database already runs as a sidecar container and code changes apply immediately from the mounted workspace.

Available convenience targets:
- `make dev` runs migrations and starts the Django development server.
- `make superuser` creates an admin user in the current environment.
- `make lint` runs Ruff and Black checks.
- `make test` runs `pytest -q`.
- `make check` runs `manage.py check`, lint, and tests.
- `make deploy-dev` starts the image-based Docker stack when Docker is available.

## Quick start (Docker host deployment)

Use the root compose file when you want to run the published container image on a machine that has Docker available.

1. Create `.env` from `.env.example` and set required values.
   - At minimum set `POSTGRES_PASSWORD`.

2. Start the stack from the repository root:
   - `docker compose up -d`

3. Create a superuser if needed:
   - `docker compose exec web python manage.py createsuperuser`

Notes:
- The root [docker-compose.yml](./docker-compose.yml) uses `image: ghcr.io/paruff/prei:latest`; it does not build the application image locally.
- Published images default `RUN_MIGRATIONS=1`, so they run `python manage.py migrate --noinput` during container startup before Gunicorn begins serving requests.
- For multi-replica or rolling deployments, set `RUN_MIGRATIONS=0` on replicas that should not apply migrations.
- Run migrations from a dedicated one-shot instance/job instead of every replica.
- Container healthchecks allow extra startup time for pre-start migration work before marking the service unhealthy.
- If you want to build locally from the repository source, use the root [Dockerfile](./Dockerfile).
- `staticfiles/` is a build artifact (generated by `collectstatic`) and is gitignored.
- In a Codespace or VS Code Dev Container, rebuild the container after changes to [.devcontainer/devcontainer.json](./.devcontainer/devcontainer.json) if you want the `docker` CLI available inside the workspace container.

## CI & tooling

- **Linting & formatting:** ruff + black
- **Type checking:** mypy (encouraged for new modules)
- **Tests:** pytest + Django testing tools — **897 passing, 1 skipped, 0 failing**
- **Documentation:** MkDocs with Material theme
- **CI:** GitHub Actions (see `.github/workflows/`) — workflows include DORA-friendly logging of deploy/test start/finish timestamps and commit SHA.

See the **[How-to Guides](https://paruff.github.io/prei/how-to-guides/)** for detailed instructions on running tests, linters, and other development tasks.

## Repository purpose

- Host the web application and all related code, tests, infra config, and documentation for the
  **passive residential real estate investment** analytics product.
- Focus on buy-and-hold SFR / small multifamily analysis, BRRRR strategy, and market intelligence.

## Contributing

Please refer to our documentation for information on how to contribute to this project. See **[How-to Guides](https://paruff.github.io/prei/how-to-guides/)** and **[Explanation](https://paruff.github.io/prei/explanation/)** sections.

## License

This project is licensed under the terms specified in the repository.
