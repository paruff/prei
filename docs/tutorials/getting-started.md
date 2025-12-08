# Getting Started with Real Estate Investor

This tutorial will walk you through setting up the Real Estate Investor application and creating your first property analysis.

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
docker-compose up --build
```

This will start both the web application and PostgreSQL database.

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

Run Django migrations to set up the database schema:

```bash
# Local development
python manage.py migrate

# Docker Compose
docker-compose exec web python manage.py migrate
```

## Step 5: Create a Superuser

Create an admin account to access the Django admin interface:

```bash
# Local development
python manage.py createsuperuser

# Docker Compose
docker-compose exec web python manage.py createsuperuser
```

Follow the prompts to set your username, email, and password.

## Step 6: Load Sample Data (Optional)

To get started quickly, you can load sample property data:

```bash
# Local development
python manage.py import_csv data/properties.csv data/rents.csv data/expenses.csv

# Docker Compose
docker-compose exec web python manage.py import_csv data/properties.csv data/rents.csv data/expenses.csv
```

## Step 7: Start the Development Server

Launch the Django development server:

```bash
# Local development
python manage.py runserver

# Docker Compose (already running)
# Access at http://localhost:8000
```

The application will be available at `http://localhost:8000`.

## Step 8: Access the Application

1. **Admin Interface:** Navigate to `http://localhost:8000/admin` and log in with your superuser credentials
2. **Dashboard:** Visit `http://localhost:8000/` to see the main dashboard (if implemented)

## Step 9: Add Your First Property

In the Django admin interface:

1. Click on **Properties**
2. Click **Add Property**
3. Fill in the property details:
   - Address, city, state, zip code
   - Purchase price and date
   - Square footage and number of units (optional)
4. Save the property

## Step 10: Add Rental Income

1. From the property's page, add **Rental Income**:
   - Monthly rent amount
   - Effective date
   - Vacancy rate (defaults to 0.05 or 5%)

## Step 11: Add Operating Expenses

1. Add **Operating Expenses** for the property:
   - Category (e.g., Property Tax, Insurance, Maintenance)
   - Amount
   - Frequency (Monthly or Annual)
   - Effective date

## Step 12: View Investment Analysis

The system automatically calculates investment metrics for each property:

- **NOI (Net Operating Income):** Annual income minus operating expenses
- **Cap Rate:** Return on investment based on NOI
- **Cash-on-Cash:** Cash return on cash invested
- **IRR (Internal Rate of Return):** Time-weighted return
- **DSCR (Debt Service Coverage Ratio):** Ability to cover debt payments

Access these metrics through the Django admin or API endpoints.

## Next Steps

Now that you have the application running, explore these guides:

- [Adding Properties and Analyzing Returns](../how-to-guides/add-property.md)
- [Understanding Financial KPIs](../reference/financial-kpis.md)
- [Importing Bulk Data](../how-to-guides/import-data.md)
- [Running Tests](../how-to-guides/running-tests.md)

## Troubleshooting

### Database Connection Issues

If you encounter database connection errors:

- **Local:** Ensure PostgreSQL is running, or remove `DATABASE_URL` from `.env` to use SQLite
- **Docker:** Verify the database service is healthy with `docker-compose ps`

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
