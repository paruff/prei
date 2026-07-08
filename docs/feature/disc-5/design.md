# DISC-5 Design: Dallas County TX NTS Scraper

## Architecture

### Layer: Integration (Scraper)
- Package: `core/integrations/county/`
- Module: `core/integrations/county/dallas_tx.py`
- Responsibilities:
  - HTTP fetch of Dallas County foreclosure page
  - HTML parsing of NTS listings
  - Data normalization into dict schema
  - Rate limiting and error handling

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
         │       ├─> HTTP GET ──> Dallas County page HTML
         │       │
         │       ├─> BeautifulSoup parse ──> list[dict]
         │       │     Fields: case_number, address, city, state, zip,
         │       │             trustee_name, lender_name, sale_date,
         │       │             opening_bid (optional)
         │       │
         │       └─> returns list[dict]
         │
         └─> for each notice:
               upsert into CountyForeclosureNotice
                 key: (case_number, county="Dallas", state="TX")
               mark stale entries as +REMOVED status?
```

## Source Integration Type
- **Type**: County Records (`SourceType.COUNTY`)
- **Method**: HTTP (requests) + HTML parsing (BeautifulSoup)
- **Status**: `COUNTY = "county"` already defined in `PipelineProperty.SourceType`

## DISC-HG-3 Dependency
The parser implementation awaits manual confirmation of:
1. The URL path(s) serving NTS listings
2. Whether the data is served as static HTML, JSON API, or requires interaction
3. The exact column/field names in the source

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
