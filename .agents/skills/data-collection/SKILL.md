> Load with: "data-collection skill" in your prompt
> Example: "Use the data-collection skill to run the VRM scraper safely."

# Data Collection Skill — prei

## When to use

Running data collection jobs, validating data freshness, handling adapter failures, or testing scrapers without hitting production APIs.

## Data sources

| Source | Scraper | Model | Management command |
|--------|---------|-------|--------------------|
| VRM Properties | `core/integrations/sources/vrm_scraper.py` | `VrmProperty` | `collect_vrm_data`, `enrich_vrm_details` |
| HUD Home Store | `core/integrations/sources/hud_scraper.py` | `ForeclosureProperty` | `fetch_hud`, `fetch_hud_source_index` |
| ATTOM API | `core/integrations/sources/attom_adapter.py` | `ForeclosureProperty` | `fetch_listings` |

## Running collection jobs

### VRM collection
```bash
python manage.py collect_vrm_data --state VA
```
- Scrapes all pages with configurable delay (default 1.5s between pages)
- Rate limiting: respect `SCRAPER_DELAY_SECONDS` setting
- Idempotent: re-running updates existing records, doesn't duplicate

### VRM enrichment
```bash
python manage.py enrich_vrm_details
```
- Fetches detail pages for properties missing enrichment data
- Runs after `collect_vrm_data` to fill in latitude/longitude, year_built, parcel_number

### HUD collection
```bash
python manage.py fetch_hud --state VA
```
- Async scraper with user-agent rotation
- 2-5 second random delay between pages
- Handles pagination automatically

### HUD source index
```bash
python manage.py fetch_hud_source_index
```

### ATTOM listings
```bash
python manage.py fetch_listings
```
- Uses ATTOM API (requires `ATTOM_API_KEY` env var)
- Has rate limiting and cost tracking via `health_monitor.py`

## Data freshness validation

After running collection, verify freshness:

```python
from django.utils import timezone
from datetime import timedelta
from core.models import VrmProperty, ForeclosureProperty

# VRM: check last scrape time
cutoff = timezone.now() - timedelta(hours=24)
stale = VrmProperty.objects.filter(updated_at__lt=cutoff).count()
total = VrmProperty.objects.count()
print(f"VRM: {stale}/{total} properties stale (>24h)")

# HUD: check data_timestamp
hud_stale = ForeclosureProperty.objects.filter(
    data_source='HUD',
    data_timestamp__lt=cutoff
).count()
```

## Health monitoring

Use `core/integrations/health_monitor.py` to check source health:

```python
from core.integrations.health_monitor import DataSourceHealthMonitor

monitor = DataSourceHealthMonitor()
# Check ATTOM API health
# Check HUD website accessibility
# Data quality scores (required + important field completeness)
# Uptime tracking (5-minute intervals)
# ATTOM cost tracking vs monthly budget
```

## Failure handling

### Common failures
| Failure | Cause | Fix |
|---------|-------|-----|
| `HUDScraperError` | Website structure changed | Check `SELECTORS` dict, update CSS selectors |
| `HUDWebsiteChangeError` | No listings found in HTML | HUD redesigned their page |
| ATTOM 401 | Invalid/expired API key | Check `ATTOM_API_KEY` env var |
| ATTOM 429 | Rate limit hit | Increase delay, check `X-RateLimit-Reset` header |
| VRM empty results | State code invalid or site down | Verify state code, check `vrmproperties.com` manually |
| `requests.Timeout` | Network issue or site slow | Retry with exponential backoff |

### Adapter testing (no production API calls)
- VRM: test with `core/tests/test_vrm_scraper.py` (uses saved HTML fixtures)
- HUD: test with `core/tests/test_hud_scraper.py`
- ATTOM: test with `core/tests/test_attom_adapter.py` (mocked API responses)
- Never hit production APIs in test suite

## Cost awareness

- ATTOM has a monthly budget (`ATTOM_MONTHLY_BUDGET` env var, default $1000)
- `health_monitor.get_cost_tracking()` tracks daily calls and spend
- Alerts at 80%, 90%, 100% of budget
- VRM and HUD are free (web scraping) but respect rate limits

## Security

- Never log or expose API keys
- ATTOM API key only in env vars, never in source
- Scrapers use `requests` with timeouts — no unbounded waits
- User-agent rotation for HUD (not spoofing, just standard practice)
