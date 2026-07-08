# Specification: Fannie Mae HomePath Property Datasource

## Problem Statement

The Property Discovery page lists Fannie Mae HomePath as a planned (non-active)
source. Users can submit `DiscoveryRequest` records for it, but no scraper
exists to fulfill those requests. Properties from HomePath — Fannie Mae's public
REO listings — are some of the most accessible foreclosure deals in the US, and
the app cannot currently discover them.

## User Need

A buy-and-hold investor using PREI should be able to:

1. Go to **Property Discovery** → see Fannie Mae HomePath as an active source
2. Enter a location (city/state or ZIP) and click **Request Properties**
3. Have the system fetch current HomePath listings for that location
4. See those listings appear in their pipeline as newly discovered properties

## Scope — In This Increment

| In scope | Out of scope |
|---|---|
| BeautifulSoup-based scraper for `homepath.com` search results | RSS feed parsing (HomePath doesn't offer one) |
| Management command `collect_fannie_mae` to run on demand or via cron | Automated scheduling (cron is future work) |
| Integration with `DiscoveryRequest` — scraper reads requests and fulfills them | Real-time incremental sync |
| Creates `PipelineProperty` records with `source_type = "fannie"` | Dedicated `FannieMaeProperty` model |
| Rate-limited scraping with configurable delay | GIS/spatial search |
| Dedup by property address | Image downloading |

## ⚠️ Known Limitation

**Determined experimentally:** `homepath.com` uses a strict Cloudflare WAF that
blocks all programmatic access. The scraper handles this gracefully (returns
empty results + warning log), but actual property discovery from this source
will require a paid data API, proxy rotation, or manual CSV import.

The infrastructure (command, dedup, pipeline integration) works fully —
only the transport layer is blocked. When a proxy or alternative data feed
is added later, it plugs into the existing command.

## Acceptance Criteria

| # | Criterion | test_type |
|---|---|---|
| AC1 | `FannieMaeHomePathClient` can search listings by city/state and return normalized dicts | unit |
| AC2 | `collect_fannie_mae` management command accepts `--location` and/or `--request-id` | unit |
| AC3 | Running the command creates `PipelineProperty` records with `source_type="fannie"` | unit |
| AC4 | Duplicate addresses (same city/state/street) are skipped, not duplicated | unit |
| AC5 | The `PropertySource.is_active` flag for Fannie Mae is set to `True` after migration | integration |
| AC6 | A `DiscoveryRequest` with `source__source_type="fannie"` can be fulfilled by the command via `--request-id` | integration |
| AC7 | Scraper respects `SCRAPER_DELAY_SECONDS` setting between requests | unit |
| AC8 | HTTP errors (4xx, 5xx, timeout) are caught and logged without crashing | unit |
