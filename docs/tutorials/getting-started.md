# Getting Started with prei

This tutorial will walk you through setting up the prei application and creating your first
property analysis with the custom design system and underwriting engine.

## Prerequisites

Before you begin, ensure you have:

- Python 3.11 or higher installed
- Git installed
- Basic familiarity with command-line interfaces
- (Optional) Docker and Docker Compose for containerized deployment

## Step 1: Clone the Repository

First, clone the repository to your local machine:

```bash
git clone git@github.com:paruff/prei.git
cd prei
```

## Step 2: Set Up Your Environment

### Option A: Local Development with Virtual Environment

Create and activate a Python virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Option B: Docker Compose (Recommended)

If you prefer containerized development, you can use Docker Compose:

```bash
docker compose up -d
```

This starts the web application with SQLite. The entrypoint automatically runs
migrations and seeds the demo user — no extra commands needed.

## Step 3: Configure Environment Variables

Copy the example environment file and customize it:

```bash
cp .env.example .env
```

Edit the `.env` file to set your configuration:

```env
DEBUG=True
SECRET_KEY=your-secure-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# For local development (SQLite)
# Leave DATABASE_URL commented out to use SQLite

# For PostgreSQL (local)
# DATABASE_URL=postgres://postgres:postgres@localhost:5432/investor_db

# For Docker Compose
DATABASE_URL=postgres://postgres:postgres@db:5432/investor_db
```

**Important:** Generate a secure `SECRET_KEY` using:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Step 4: Initialize the Database

The entrypoint runs migrations and seeds the demo user automatically on container start.

```bash
# Local development
python manage.py migrate
python manage.py seed_data

# Docker Compose (entrypoint handles it — just start the container)
docker compose up -d
```

## Step 5: Load Sample Data (Optional, if not auto-seeded)

If the entrypoint didn't run (e.g. local virtualenv), seed the demo user manually:

```bash
python manage.py seed_data
```

This creates a demo user and sample properties:
- Email: `demo@prei.dev`
- Password: `DemoPass123!`

### Create a Superuser (Optional — for Django Admin access)

Create an admin account to access the Django admin interface:

```bash
# Local development
python manage.py createsuperuser

# Docker Compose
docker compose exec web python manage.py createsuperuser
```

## Step 6: Start the Development Server

Launch the Django development server:

```bash
# Local development
python manage.py runserver

# Docker Compose (already running)
# Access at http://localhost:8000
```

The application will be available at `http://localhost:8000`.

## Step 7: Explore the Application

1. **Dashboard** — Visit `http://localhost:8000/` to see the deal screener dashboard with
   KPI grid, colour-coded verdicts, and property list
2. **Add a Property** — Use the property entry form (`/properties/add/`) with styled inputs
   and responsive form grids
3. **BRRRR Calculator** — Navigate to `/brrrr/` to try the fully client-side BRRRR calculator
4. **Markets** — Browse `/markets/` for market intelligence scores per ZIP
5. **Admin Interface** — Navigate to `http://localhost:8000/admin` for Django admin access

### UI/UX Highlights

The interface is built on a **custom design system** with:

- **CSS custom property tokens** (`tokens.css`) — semantic colors, spacing, typography
- **Component classes** — `.card`, `.kpi-grid`, `.data-table`, `.verdict-badge`, `.score-bar`,
  `.tab-bar`, `.brrrr-banner`, `.empty-state`
- **Responsive layout** — 4-column → 2-column → 1-column at 640px / 400px breakpoints
- **No Bootstrap** — zero third-party CSS frameworks
- **Widget base classes** — `StyledNumberInput`, `StyledTextInput`, `StyledSelect` auto-apply
  CSS in `core/forms.py`
- **Python-driven colors** — `score.coc_color_class` properties return CSS class names; no
  threshold logic in templates

## Step 8: Add Your First Property

1. Click **Add Property** from the dashboard or navigate to `/properties/add/`
2. Fill in the property details:
   - Address, city, state, zip code
   - Purchase price and date (e.g. $200,000)
   - Square footage and number of units
   - Financing details (down payment %, interest rate, loan term)
   - Operating expenses (taxes, insurance, HOA, maintenance, capex)
3. Save the property
4. The dashboard will now show the property with its underwriting score and verdict

## Step 9: View Investment Analysis

Each property receives a full underwriting scorecard:

- **Underwriting Score** — 0–100 composite score
- **Verdict** — "Strong Buy", "Conditional", or "Pass"
- **Metrics** — CoC, Cap Rate, DSCR, GRM, After-Tax CoC, IRR
- **Flags** — Any failing criteria with explanations
- **Color coding** — Green (good), amber (warning), red (bad)

## Next Steps

Now that you have the application running, explore these guides:

- [Using the BRRRR Calculator](../how-to-guides/use-brrrr-calculator.md)
- [Understanding Financial KPIs](../reference/financial-kpis.md)
- [Importing Bulk Data](../how-to-guides/import-data.md)
- [Running Tests](../how-to-guides/running-tests.md)
- [Design System Reference](../explanation/design-system.md)

## Troubleshooting

### Database Connection Issues

If you encounter database connection errors:

- **Local:** Ensure PostgreSQL is running, or remove `DATABASE_URL` from `.env` to use SQLite
- **Docker:** Verify the database service is healthy with `docker compose ps`

### Missing Static Files

If the UI appears unstyled or tests fail with `Missing staticfiles manifest entry`:

```bash
python manage.py collectstatic --noinput
```

### Migration Errors

If migrations fail:

```bash
# Check migration status
python manage.py showmigrations

# Reset migrations (development only!)
python manage.py migrate core zero
python manage.py migrate
```

### Port Already in Use

If port 8000 is already in use:

```bash
# Use a different port
python manage.py runserver 8001
```

## Getting Help

If you encounter issues not covered here, please:

- Check the [How-to Guides](../how-to-guides/index.md) for specific tasks
- Review the [Reference documentation](../reference/index.md)
- Open an issue on [GitHub](https://github.com/paruff/prei/issues)
