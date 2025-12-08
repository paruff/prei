# Foreclosure Data Integrations

This module provides data source integrations for fetching foreclosure property data from external sources.

## Overview

The integrations module supports multiple data sources:

1. **ATTOM API** - Commercial foreclosure and property data API
2. **HUD Home Store** - Government foreclosure listings web scraper
3. **Health Monitoring** - Data source health checks and quality monitoring

## Features

### ATTOM API Integration (`sources/attom_adapter.py`)

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
```

### HUD Home Store Scraper (`sources/hud_scraper.py`)

The HUD scraper provides:
- **HTML Parsing** - BeautifulSoup-based property extraction
- **Address Parsing** - Intelligent parsing of various address formats
- **Property ID Generation** - Deterministic IDs from addresses for deduplication
- **Error Resilience** - Continues processing even with malformed listings
- **Rate Limiting** - Built-in delays between requests

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

**Note:** The current implementation is a placeholder. For production use, implement with Playwright to handle JavaScript-rendered content. See the TODO in `scrape_state()` method for requirements.

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
pytest core/tests/test_attom_adapter.py      # 25 tests
pytest core/tests/test_hud_scraper.py        # 30 tests
pytest core/tests/test_health_monitor.py     # 14 tests
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

1. **Caching Strategy** - 24-hour cache for ATTOM API to balance freshness and cost
2. **Error Handling** - Fail gracefully with logging; don't stop processing on individual errors
3. **Type Safety** - Use Decimal for currency to avoid floating-point errors
4. **Testing** - Comprehensive unit tests with mocked external dependencies
5. **Security** - Environment-based configuration; no secrets in code

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
