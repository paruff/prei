# Data Integrations

This module provides data source integrations for fetching foreclosure and market data from external sources.

## Overview

The integrations module supports multiple data source categories:

### Foreclosure Data Sources

1. **ATTOM API** - Commercial foreclosure and property data API
2. **HUD Home Store** - Government foreclosure listings web scraper
3. **Health Monitoring** - Data source health checks and quality monitoring

### Market Data Sources (`core/integrations/market/`)

| Adapter | Module | Status | Key Required | Returns |
|---|---|---|---|---|
| **Rent Estimate** | `market/rents.py` | 🟢 Live (RentCast) | `RENTCAST_API_KEY` | `Decimal` rent or `None` |
| **School Rating** | `market/schools.py` | 🟢 Live (GreatSchools) | `GREATSCHOOLS_API_KEY` | `Decimal` rating or `None` |
| **Walk Score** | `market/walkability.py` | 🟢 Live (Walk Score API) | `WALKSCORE_API_KEY` | `dict` with scores or `None` |
| **Comps** | `market/comps.py` | 🟡 Live→Dummy fallback (ATTOM) | `ATTOM_API_KEY` | `List[dict]` comps or `[]` |
| **Crime** | `market/crime.py` | 🔴 Dummy only (see DECISION-2) | None needed | `Decimal` dummy score |
| **Census Demographics** | `market/demographics.py` | 🟢 Live (Census API) | `CENSUS_API_KEY` | `dict` demographics or `None` |
| **BLS Unemployment** | `market/employment.py` | 🟢 Live (BLS API) | `BLS_API_KEY` | `Decimal` rate or `None` |

## Market Data Integrations

### Rent Estimate (`market/rents.py`)

Uses the RentCast API to fetch rental estimates for a property address. Returns `Decimal` or `None`.

**Real adapter:** `fetch_rent_estimate(address, zip_code, api_key)` — calls RentCast API, caches results for 24h.
**Dummy fallback:** `get_rent_estimate_for_listing(listing)` — returns a hardcoded estimate (1% of price).

```bash
RENTCAST_API_KEY=your_api_key_here
```

### School Rating (`market/schools.py`)

Uses the GreatSchools API to fetch school ratings for a ZIP code. Returns `Decimal` (average of all schools) or `None`.

**Real adapter:** `fetch_school_rating(zip_code, api_key)` — calls GreatSchools API, caches results for 24h.
**Dummy fallback:** `get_school_rating(zip_code)` — returns a hardcoded 6.0 rating.

```bash
GREATSCHOOLS_API_KEY=your_api_key_here
```

### Walk Score (`market/walkability.py`)

Uses the Walk Score API to fetch walk/transit/bike scores. Returns a dict or `None`.

**Real adapter:** `fetch_walk_score(address, api_key)` — calls Walk Score API.

```bash
WALKSCORE_API_KEY=your_api_key_here
```

### Comps (`market/comps.py`)

Fetches comparable sales using the ATTOM API sales history endpoint (reuses `ATTOM_API_KEY`). Returns `List[Dict]` or `[]` on failure.

**Real adapter:** `fetch_comps_for_listing(listing, api_key=None)` — calls ATTOM `/sale/snapshot`.
**Dummy fallback:** `get_comps_for_listing(listing)` — generates synthetic comps at 90%/100%/110% of listing price.

### Crime (`market/crime.py`)

**Dummy only.** Per DECISION-2 (see `crime.py` module docstring), no live crime data integration is recommended. The FBI Crime Data Explorer API requires a registered api.data.gov key, and its terms of service and geography-level capabilities are unverifiable without an active key.

Returns `Decimal("1.0")` for TX, `Decimal("7.0")` for CA, `Decimal("3.0")` otherwise.

### Census Demographics (`market/demographics.py`)

Uses Census API to fetch population and growth data for a ZIP code. Returns dict or `None`.

```bash
CENSUS_API_KEY=your_api_key_here
```

### BLS Unemployment (`market/employment.py`)

Uses BLS API to fetch unemployment rate for a state. Returns `Decimal` fraction or `None`.

```bash
BLS_API_KEY=your_api_key_here
```

### Service Layer (`core/services/market_data.py`)

The `refresh_market_snapshot(zip_code)` function orchestrates all adapters with a live→dummy fallback pattern:

1. Calls the real adapter first (if its API key is set)
2. Falls back to the dummy adapter on `None` or empty return
3. Sets the `data_source` field on `MarketSnapshot` — `"dummy"` if all dummy, or comma-separated adapter names (e.g. `"rentcast,greatschools"`) for live sources

## Features

The ATTOM adapter provides:
- **Authentication** - Secure API key management via environment variables
- **Rate Limiting** - Automatic handling of API rate limits
- **Caching** - 24-hour cache to reduce API costs and handle rate limits
- **Error Handling** - Comprehensive error handling with specific exceptions
- **Cost Tracking** - Monitor API usage and costs against budget
- **Data Normalization** - Maps ATTOM responses to `ForeclosureProperty` model

#### Usage Example

```python
from core.integrations.sources.attom_adapter import ATTOMAdapter

# Initialize adapter (reads ATTOM_API_KEY from environment)
adapter = ATTOMAdapter()

# Fetch property details with caching
property_data = adapter.fetch_with_cache(
    "123 Ocean Drive",
    "Miami, FL 33139"
)

# Normalize to ForeclosureProperty schema
normalized = adapter.normalize_property(property_data)

# Track API usage
stats = adapter.get_usage_stats(days=30)
print(f"Total calls: {stats['total_calls']}")
print(f"Total cost: ${stats['total_cost']}")
```

#### Environment Variables

```bash
ATTOM_API_KEY=your_api_key_here
ATTOM_COST_PER_CALL=0.01          # Cost per API call
ATTOM_MONTHLY_BUDGET=1000.00       # Monthly budget limit

# Market data API keys (optional — dummy fallbacks used when not set)
RENTCAST_API_KEY=your_rentcast_key
GREATSCHOOLS_API_KEY=your_greatschools_key
WALKSCORE_API_KEY=your_walkscore_key
CENSUS_API_KEY=your_census_api_key
BLS_API_KEY=your_bls_api_key
```

### HUD Home Store Scraper (`sources/hud_scraper.py`)

The HUD scraper provides:
- **HTML Parsing** - BeautifulSoup-based property extraction
- **Address Parsing** - Intelligent parsing of various address formats
- **Property ID Generation** - Deterministic IDs from addresses for deduplication
- **Error Resilience** - Continues processing even with malformed listings
- **Rate Limiting** - Built-in delays between paginated requests
- **Pagination Support** - Follows next-page links while staying on HUD domain

#### Usage Example

```python
from core.integrations.sources.hud_scraper import HUDHomeScraper
import asyncio

scraper = HUDHomeScraper()

# Scrape properties for a state
properties = asyncio.run(scraper.scrape_state("FL"))

# Extract properties from HTML
html = fetch_hud_page_html()
properties = scraper.extract_properties_from_html(html)
```

**Note:** The current implementation supports HTML page fetch + parsing + pagination.
For complex JavaScript-rendered flows, a Playwright-based implementation may still be needed.

### Health Monitoring (`health_monitor.py`)

The health monitor provides:
- **API Health Checks** - Periodic pings to verify data source availability
- **Data Quality Scoring** - Calculates completeness scores for property data
- **Cost Tracking** - Monitors ATTOM API usage against budget thresholds
- **Uptime Calculation** - Tracks source uptime percentages
- **Alerting** - Automatic alerts at 80%, 90%, 100% budget thresholds

#### Usage Example

```python
from core.integrations.health_monitor import DataSourceHealthMonitor
import asyncio

monitor = DataSourceHealthMonitor()

# Check all sources
health_status = asyncio.run(monitor.check_all_sources())

# Get data quality score
quality = monitor.calculate_data_quality_score("ATTOM", days=7)
print(f"Quality score: {quality['score']}%")

# Get cost tracking
cost_data = monitor.get_cost_tracking("attom", days=30)
if "alert" in cost_data:
    print(f"Alert: {cost_data['alert']}")

# Get comprehensive dashboard data
dashboard = monitor.get_health_dashboard_data()
```

## Testing

All integrations have comprehensive unit tests:

```bash
# Run all integration tests
pytest core/tests/test_attom_adapter.py      # ATTOM adapter
pytest core/tests/test_hud_scraper.py        # HUD scraper
pytest core/tests/test_health_monitor.py     # Health monitoring
pytest core/tests/test_market_adapters_v2.py # RentCast, GreatSchools, WalkScore
pytest tests/test_market_adapters_v2.py      # Comps + market_data wiring
pytest tests/test_market_adapters.py         # Census, BLS, snapshot cache
```

## Security

- All dependencies scanned for vulnerabilities
- CodeQL security scanning: 0 alerts
- API keys stored in environment variables, never in code
- Input validation on all external data
- Safe type conversions with error handling

## Error Handling

The module defines specific exception classes:

- `ATTOMAPIError` - Base ATTOM API error
- `ATTOMAuthenticationError` - Invalid or expired credentials
- `ATTOMRateLimitError` - Rate limit exceeded
- `HUDScraperError` - Base HUD scraper error
- `HUDWebsiteChangeError` - Website structure changed

## Data Model Integration

All adapters normalize data to the `ForeclosureProperty` model defined in `core/models.py`:

```python
class ForeclosureProperty(models.Model):
    property_id = models.CharField(max_length=128, unique=True)
    data_source = models.CharField(max_length=64)  # "ATTOM" or "HUD"

    # Address
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=2)
    zip_code = models.CharField(max_length=16)

    # Foreclosure details
    foreclosure_status = models.CharField(max_length=32)
    opening_bid = models.DecimalField(...)
    auction_date = models.DateField(...)

    # Property details
    bedrooms = models.PositiveIntegerField()
    bathrooms = models.DecimalField(...)
    square_footage = models.PositiveIntegerField()
    # ... and more
```

## Future Enhancements

### Phase 5: Scheduled Tasks (Planned)

- Celery configuration for background tasks
- Scheduled HUD scraping (daily at 2 AM)
- Task monitoring and retry logic
- Management commands for manual execution

### Production Deployment

1. **ATTOM API**
   - Configure API key in production environment
   - Set appropriate budget limits
   - Monitor cost alerts
   - Configure Redis for caching

2. **HUD Scraper**
   - Implement Playwright-based scraper
   - Deploy with browser automation support
   - Schedule nightly scrapes
   - Monitor for website changes

3. **Health Monitoring**
   - Set up monitoring dashboard
   - Configure alerting (email, Slack, PagerDuty)
   - Establish SLA thresholds
   - Create runbooks for common issues

## Architecture Decisions

1. **Caching Strategy** - 24-hour cache for ATTOM/RentCast/GreatSchools APIs to balance freshness and cost
2. **Live→Dummy Fallback** - All market adapters try the real API first, then fall back to deterministic dummy data, then default to 0. This ensures `refresh_market_snapshot` never fails
3. **data_source Tracking** - `MarketSnapshot.data_source` distinguishes `"dummy"` snapshots from live-sourced ones (e.g. `"rentcast,greatschools"`) to avoid silent quality degradation
4. **Crime is Dummy** - FBI CDE API requires a registered api.data.gov key with unverifiable TOS; crime adapter is intentionally dummy-only (DECISION-2 Option C)
5. **Error Handling** - Fail gracefully with logging; don't stop processing on individual errors
6. **Type Safety** - Use Decimal for currency to avoid floating-point errors
7. **Testing** - Comprehensive unit tests with mocked external dependencies
8. **Security** - Environment-based configuration; no secrets in code

## Contributing

When adding new data sources:

1. Create an adapter in `sources/` following the pattern of existing adapters
2. Implement a `fetch()` function that returns normalized property dictionaries
3. Add comprehensive unit tests
4. Update health monitoring to include the new source
5. Document usage and configuration
6. Add security scanning for any new dependencies

## License

See repository LICENSE file.
