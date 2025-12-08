# Architecture Overview

This document explains the high-level architecture of the Real Estate Investor application, its components, and how they interact.

## System Overview

Real Estate Investor is a Django-based web application designed as a monolithic architecture with clear separation of concerns. The application follows Django's Model-View-Template (MVT) pattern with additional organization for financial calculations.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                         │
│  (Web Browser, Admin Interface, Future API Clients)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Django     │  │   Templates  │  │   REST API   │     │
│  │   Admin      │  │   (Future)   │  │   (Future)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Business Logic Layer                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Views      │  │  Management  │  │   Finance    │     │
│  │              │  │  Commands    │  │   Utils      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Data Access Layer                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Django ORM (Models)                     │  │
│  │  Property │ RentalIncome │ OperatingExpense │ etc.  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Persistence Layer                      │
│         PostgreSQL (production) / SQLite (local dev)        │
└─────────────────────────────────────────────────────────────┘
```

## Component Organization

### Django Project Structure

The application follows Django's standard project organization with custom apps:

```
investor_app/              # Django project root
├── settings.py            # Main configuration
├── settings_test.py       # Test-specific settings
├── urls.py                # URL routing
├── wsgi.py                # WSGI application
├── asgi.py                # ASGI application (future)
└── finance/               # Financial utilities package
    ├── __init__.py
    └── utils.py           # KPI calculation functions

core/                      # Main Django app
├── models.py              # Data models
├── views.py               # View logic
├── admin.py               # Admin interface configuration
├── urls.py                # App-level URL routing
├── management/            # Management commands
│   └── commands/
│       └── import_csv.py  # CSV import command
└── tests/                 # Test suite
    ├── conftest.py        # Test fixtures
    └── test_*.py          # Test modules
```

### Separation of Concerns

1. **Models (Data Layer)**
   - Define data structure and relationships
   - Provide data validation
   - Implement business rules at the model level
   - Located in `core/models.py`

2. **Finance Utilities (Business Logic)**
   - Centralized financial calculations
   - Pure functions for testability
   - Use Decimal for precision
   - Located in `investor_app/finance/utils.py`

3. **Views (Presentation Logic)**
   - Handle HTTP requests/responses
   - Coordinate between models and templates
   - Trigger financial calculations
   - Located in `core/views.py`

4. **Admin Interface (UI Layer)**
   - Django's built-in admin for CRUD operations
   - Customized for property management
   - Located in `core/admin.py`

## Data Flow

### Property Analysis Calculation Flow

```
1. User creates/updates Property via Admin
         │
         ▼
2. User adds RentalIncome and OperatingExpense records
         │
         ▼
3. User or system triggers analysis calculation
         │
         ▼
4. compute_analysis_for_property() called
         │
         ├─► Fetch rental income records
         ├─► Fetch operating expense records
         ├─► Calculate monthly totals
         │
         ▼
5. Call financial utility functions
         │
         ├─► noi(monthly_income, monthly_expenses)
         ├─► cap_rate(noi, purchase_price)
         ├─► cash_on_cash(cash_flow, cash_invested)
         ├─► irr(cashflows)
         └─► dscr(noi, debt_service)
         │
         ▼
6. Store results in InvestmentAnalysis model
         │
         ▼
7. Display results in Admin or API response
```

### CSV Import Flow

```
1. User runs: python manage.py import_csv properties.csv rents.csv expenses.csv
         │
         ▼
2. Management command parses CSV files
         │
         ├─► Validate headers and data types
         ├─► Check foreign key references
         └─► Handle errors gracefully
         │
         ▼
3. Create database records in transaction
         │
         ├─► Import Properties first
         ├─► Import RentalIncome (references Properties)
         └─► Import OperatingExpenses (references Properties)
         │
         ▼
4. Return summary of imported records
```

## Key Design Decisions

### 1. Decimal Precision for Financial Data

**Decision:** Use Python's `Decimal` type for all currency values and percentages.

**Rationale:**
- Floating-point arithmetic can introduce rounding errors in financial calculations
- `Decimal` provides exact decimal representation
- Django's `DecimalField` integrates seamlessly with `Decimal`

**Implementation:**
```python
# Model field
purchase_price = models.DecimalField(max_digits=12, decimal_places=2)

# Calculation
noi = Decimal(monthly_income) * Decimal(12) - Decimal(monthly_expenses) * Decimal(12)
```

### 2. Centralized Financial Calculations

**Decision:** All financial KPI calculations are in `investor_app/finance/utils.py`.

**Rationale:**
- Single source of truth for calculation logic
- Easy to test in isolation
- Consistent calculations across the application
- Supports future API or batch processing

**Alternative Considered:** Model methods (e.g., `property.calculate_noi()`)
- **Rejected because:** Harder to test, mixes data and business logic

### 3. Separate InvestmentAnalysis Model

**Decision:** Store calculated KPIs in a separate `InvestmentAnalysis` model.

**Rationale:**
- Avoids recalculating on every query
- Enables historical tracking of KPI changes
- Supports caching and performance optimization
- Explicit `updated_at` timestamp for staleness detection

**Trade-off:** Requires keeping analysis in sync with underlying data

### 4. PostgreSQL with SQLite Fallback

**Decision:** Use PostgreSQL in production, allow SQLite for local development.

**Rationale:**
- PostgreSQL for production performance and reliability
- SQLite for quick local setup without Docker
- Django abstracts database differences

**Configuration:**
```python
# settings.py
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", ...}}
```

### 5. Django Admin as Primary UI (MVP)

**Decision:** Use Django's built-in admin interface for MVP.

**Rationale:**
- Rapid development without frontend code
- Full CRUD operations out-of-the-box
- Customizable for specific needs
- Focus MVP effort on calculations and data model

**Future:** Build custom frontend with React or Vue.js

### 6. Environment-Driven Configuration

**Decision:** All configuration through environment variables.

**Rationale:**
- Security: No secrets in source code
- Flexibility: Same codebase for dev/staging/production
- 12-Factor App compliance
- Easy Docker and CI/CD integration

**Implementation:**
```python
import environ
env = environ.Env()
DEBUG = env.bool("DEBUG", default=False)
SECRET_KEY = env("SECRET_KEY")
```

### 7. Three-Layer Testing Strategy

**Decision:** Implement unit, integration, and BDD tests.

**Rationale:**
- **Unit tests:** Fast, isolated tests for financial functions
- **Integration tests:** Test Django components together
- **BDD tests:** Validate user workflows with Gherkin syntax

**Benefits:**
- Comprehensive coverage
- Fast feedback from unit tests
- Confidence in system behavior from integration/BDD tests

### 8. Simplified IRR Calculation (MVP)

**Decision:** Use 12-month cash flow projection for IRR in MVP.

**Rationale:**
- Sufficient for initial property screening
- Avoids complexity of multi-year projections
- Easy to understand and verify

**Future Enhancement:** Support custom holding periods and exit assumptions

## Scalability Considerations

### Current MVP Limitations

1. **Single-server deployment** — Not designed for horizontal scaling
2. **Synchronous processing** — All calculations happen in request/response cycle
3. **No caching layer** — Each request recalculates or queries database
4. **Limited concurrent users** — Django development server is single-threaded

### Future Scaling Strategies

1. **Caching:**
   - Redis for calculated KPIs
   - Invalidate on property/income/expense updates

2. **Async Processing:**
   - Celery for background KPI recalculation
   - Queue-based CSV imports for large files

3. **Database Optimization:**
   - Indexes on frequently queried fields
   - Read replicas for reporting queries
   - Partitioning for very large datasets

4. **API Gateway:**
   - Separate read and write operations
   - Rate limiting and authentication
   - CDN for static assets

## Security Considerations

### Current Security Measures

1. **Authentication:** Django's built-in user authentication
2. **Authorization:** User-based property ownership (ForeignKey to User)
3. **Input Validation:** Model-level validation and form validation
4. **SQL Injection Protection:** Django ORM parameterized queries
5. **CSRF Protection:** Django's CSRF middleware
6. **Secret Management:** Environment variables for sensitive data

### Future Security Enhancements

1. Multi-factor authentication
2. Role-based access control (RBAC)
3. Audit logging for all data changes
4. Rate limiting on API endpoints
5. Encryption at rest for sensitive data

## Integration Points

### Current Integrations

1. **PostgreSQL** — Primary database
2. **NumPy/NumPy-Financial** — Financial calculations

### Future Integration Opportunities

1. **Third-party data sources:**
   - Zillow/Redfin for property valuations
   - Rentometer for market rent data
   - Tax assessment databases

2. **Financial services:**
   - Mortgage calculators
   - Loan servicing platforms

3. **Reporting and analytics:**
   - Export to Excel/CSV
   - Integration with BI tools (Tableau, Power BI)

## Deployment Architecture

### Local Development

```
Developer Machine
├── Python virtual environment
├── SQLite database (optional)
└── Django development server (port 8000)
```

### Docker Compose Development

```
Docker Host
├── Web Container (Django app)
│   ├── Python 3.11
│   ├── Application code
│   └── Port 8000
└── Database Container (PostgreSQL)
    ├── PostgreSQL 15
    └── Port 5432 (internal)
```

### Production (Future)

```
Cloud Provider (AWS/GCP/Azure)
├── Load Balancer
│   └── HTTPS termination
├── Application Servers (multiple instances)
│   ├── Django + Gunicorn
│   └── Horizontal scaling
├── Database Server
│   ├── PostgreSQL (managed service)
│   └── Automated backups
├── Caching Layer
│   └── Redis (managed service)
└── Object Storage
    └── Static files (S3/GCS)
```

## Technology Constraints and Assumptions

### Assumptions

1. **User base:** Initially small (< 100 users)
2. **Property count:** Dozens to hundreds per user
3. **Calculation frequency:** On-demand, not real-time
4. **Data volume:** Moderate (< 1 million records)

### Constraints

1. **Python ecosystem:** Limited to Python-compatible libraries
2. **Django framework:** Bound by Django's architecture and patterns
3. **Single currency:** Currently assumes USD
4. **Tax implications:** Does not calculate tax liability

## Related Documentation

- [Technology Choices](technology-choices.md) — Detailed technology selection rationale
- [Data Model Design](data-model-design.md) — Database schema and relationships
- [Testing Strategy](testing-strategy.md) — Test architecture and approach
- [Financial Calculation Philosophy](financial-philosophy.md) — KPI calculation approach
