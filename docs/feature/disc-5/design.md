# DISC-5 Design: Dallas County TX NTS Scraper

## Architecture

### Layer: Integration (Scraper)
- Package: `core/integrations/county/`
- Module: `core/integrations/county/dallas_tx.py`
- Responsibilities:
  - Playwright-based (headless Chromium) fetch of React SPA
  - HTML parsing of NTS listings from rendered DOM
  - Data normalization into dict schema
  - Graceful empty-result fallback when auth required

### Layer: Management Command
- Module: `core/management/commands/scrape_dallas_county_nts.py`
- Responsibilities:
  - Accept CLI args (`--dry-run`, `--days`)
  - Call scraper, iterate results, upsert into `CountyForeclosureNotice`
  - Stale record detection and removal

### Layer: Tests
- Package: `core/tests/test_county/`
- Module: `core/tests/test_county/test_dallas_tx.py`
- Fixture: HTML snapshot mimicking Dallas County's foreclosure page structure

## Data Flow

```
CLI ──> scrape_dallas_county_nts command
         │
         ├─> dallas_tx.scrape_dallas_county_nts()
         │       │
         │       ├─> Playwright (headless Chromium)
         │       │       └─> publicsearch.us React SPA
         │       │              │
         │       │              ├─> Login wall detected? → return None (logged)
         │       │              └─> Table rendered? → _parse_rendered_html()
         │       │
         │       ├─> _parse_rendered_html() ──> list[dict]
         │       │     Fields: case_number, address, city, state, zip,
         │       │             trustee_name, lender_name, sale_date,
         │       │             opening_bid (optional)
         │       │
         │       └─> returns list[dict] (or [] if unavailable)
         │
         └─> for each notice:
               upsert into CountyForeclosureNotice
                 key: (case_number, county="Dallas", state="TX")
```

## Source Integration Type
- **Type**: County Records (`SourceType.COUNTY`)
- **Method**: Playwright (headless Chromium) + BeautifulSoup DOM parsing
- **Status**: Returns empty results; data is behind publicsearch.us login wall

## DISC-HG-3 Resolution (2026-07-08)

The Dallas County foreclosure data is served through **publicsearch.us** (a React SPA
powered by the Neumo platform), *not* the direct county website.

Confirmed findings:
1. **URL**: `https://dallas.tx.publicsearch.us/results?department=FC&instrumentDateRange=...`
2. **Format**: React SPA — requires JavaScript rendering (Playwright)
3. **Auth**: The portal requires a **user account**. Unauthenticated requests hit a login wall.
4. **Fields**: Not confirmed — DOM inspection requires an authenticated session.

The scraper has been updated to use Playwright (like `fannie_mae.py`) and gracefully
returns empty results with a warning when the login wall is encountered. To make this
scraper functional, obtain a publicsearch.us account and either:
- Add a Playwright-based Sign In flow
- Reverse-engineer the JSON API from a logged-in session's network tab

## File Inventory

| File | Purpose |
|---|---|
| `core/integrations/county/__init__.py` | Package init |
| `core/integrations/county/dallas_tx.py` | Scraper module |
| `core/management/commands/scrape_dallas_county_nts.py` | Management command |
| `core/tests/test_county/__init__.py` | Test package |
| `core/tests/test_county/test_dallas_tx.py` | Tests + fixture data |
| `docs/feature/disc-5/spec.md` | Specification |
| `docs/feature/disc-5/design.md` | This document |
