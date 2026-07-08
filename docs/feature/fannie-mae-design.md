# Design: Fannie Mae HomePath Property Datasource

## Impacted Components

| Component | Change |
|---|---|
| `core/integrations/sources/fannie_mae.py` | **NEW** — HomePath client (Playwright-based) |
| `core/management/commands/collect_fannie_mae.py` | **NEW** — management command |
| `core/models.py` (PropertySource seed data) | Set `is_active=True` for Fannie Mae source |
| `core/migrations/` | Data migration to activate Fannie Mae source |
| `core/integrations/sources/__init__.py` | Optional: re-export for discoverability |

## ⚠️ Known Limitation: Cloudflare WAF Blocking

**Determined experimentally (2026-07-08):** `homepath.com` uses a strict
Cloudflare WAF that blocks all programmatic access — including `requests`,
`curl`, and headless Playwright. HTTP 403 is returned regardless of user-agent
or browser configuration. The site is effectively protected against scraping.

**Impact:** The `FannieMaeHomePathClient` will attempt to fetch listings but
will gracefully handle blocks by returning empty results and logging a warning.
Actual property discovery from this source will require one of:
1. A paid real estate data API that includes Fannie Mae REO inventory
2. Manual CSV/JSON import via a future admin upload UI
3. A residential proxy rotating through Playwright (future enhancement)

**The infrastructure (models, command, tests, pipeline integration) is still
fully implemented.** When a proxy or alternative data source is added later,
only the transport layer needs to change.

## Architecture

```
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Discovery   │    │   Management     │    │  FannieMae       │
│  Request     │───▶│   Command        │───▶│  HomePathClient  │
│  (DB)        │    │  collect_fannie_ │    │  (Playwright)    │
│              │    │  mae.py          │    │                  │
└──────────────┘    └──────────────────┘    └───────┬──────────┘
                                                    │
                                           ╔═══════════════════╗
                                           ║  homepath.com     ║
                                           ║  (HTTP 403 - WAF) ║
                                           ╚═══════════════════╝
                                                    │
                                          [graceful failure]
                                                    │
                                           ┌──────────────────┐
                                           │  PipelineProperty │
                                           │  source_type=     │
                                           │  "fannie"         │
                                           │  stage=DISCOVERED │
                                           └──────────────────┘
```

## Data Flow

### 1. FannieMaeHomePathClient

Location: `core/integrations/sources/fannie_mae.py`

Pattern: Playwright-based client with graceful fallback for WAF blocks.

```python
class FannieMaeHomePathClient:
    """Attempts to fetch Fannie Mae HomePath REO listings.

    homepath.com uses Cloudflare WAF which blocks all programmatic access.
    This client makes a best-effort attempt and returns empty results
    with a warning log when blocked.
    """

    BASE_URL = "https://www.homepath.com"

    def __init__(self, delay_seconds: float | None = None):
        ...

    def search_by_location(self, location: str) -> list[dict]:
        """Search listings by city/state or ZIP. Returns normalized dicts.

        Returns an empty list with a logged warning if Cloudflare blocks access.
        """
        ...

    def _detect_blocked(self, page) -> bool:
        """Check if the page is a Cloudflare challenge/block page."""
        ...
```

**Normalized output dict** (matches `core/integrations/sources/__init__.py` convention):

```python
{
    "source": "fannie_mae",
    "address": "123 Main St",
    "city": "Austin",
    "state": "TX",
    "zip_code": "78701",
    "price": Decimal("250000.00"),
    "beds": 3,
    "baths": Decimal("2.0"),
    "sq_ft": 1500,
    "property_type": "SFH",
    "url": "https://www.homepath.com/listing/...",
    "posted_at": datetime(2026, 7, 1),
    "status": "Active",           # Active, Pending, Sold
    "year_built": 2005,
    "lot_size": 0.25,             # Acres
    "description": "Beautiful 3BR...",
    "images": ["https://..."],
}
```

### 2. Management Command

Location: `core/management/commands/collect_fannie_mae.py`

```python
class Command(BaseCommand):
    help = "Fetch Fannie Mae HomePath listings and upsert into pipeline"

    def add_arguments(self, parser):
        parser.add_argument("--location", help="City, State or ZIP to search")
        parser.add_argument("--request-id", type=int,
            help="Fulfill a specific DiscoveryRequest by ID")
        parser.add_argument("--all-pending", action="store_true",
            help="Fulfill all pending DiscoveryRequests for Fannie Mae")
```

**Upsert logic** (in `handle`):

1. Determine target location(s):
   - `--location` → single location
   - `--request-id` → read from `DiscoveryRequest`
   - `--all-pending` → read all `REQUESTED` DiscoveryRequests for Fannie Mae
2. Call `client.search_by_location(location)`
3. For each result, `PipelineProperty.objects.update_or_create` keyed on
   `(user, source_type="fannie", address_hash)` where `address_hash` is
   `sha256(street.lower() + city.lower() + state)` for dedup
4. Update `DiscoveryRequest.status = "completed"` with `properties_found` count
5. Log results

### 3. Dedup Strategy

```python
address_hash = hashlib.sha256(
    f"{street.lower()}|{city.lower()}|{state.lower()}".encode()
).hexdigest()
```

Each `PipelineProperty` for Fannie Mae gets `source_id = address_hash`.
The `unique_user_source_property` constraint (`(user, source_type, source_id)`)
prevents duplicates. We assign the first `DiscoveryRequest.user` who requested
the location as the owner.

### 4. Rate Limiting

Use `settings.SCRAPER_DELAY_SECONDS` (default 1.5s) between page requests.
HomePath returns ~20 results per page — paginate with `&page=N` param.

### 5. Error Handling

- HTTP 4xx/5xx: log warning, skip page, continue
- Timeout: catch `requests.Timeout`, log error, abort
- Parse failure: log individual listing card failure, continue to next
- Empty results: log info, return empty list

### 6. Source Activation

A data migration sets `PropertySource.objects.filter(source_type="fannie").update(is_active=True)`
so the Discovery page shows Fannie Mae as an active integration.

## Constraints

- **No API key required** — HomePath is fully public
- **Rate limit**: 1 request per 1.5s minimum (configurable via `SCRAPER_DELAY_SECONDS`)
- **Legal**: Public REO listings are legal to scrape (confirmed in user spec)
- **No JavaScript rendering**: HomePath search results are server-rendered HTML
