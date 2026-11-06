# core/management/commands

## Overview
`manage.py` commands (each a `Command(BaseCommand)`) for seeding demo data, ingesting REO and foreclosure sources, and refreshing market data.

## Interface
Run as `python manage.py <name>`. Arguments from `add_arguments`:
- Seeding: `seed_data` (reset flag), `seed_market` (`--state`, `--city`), `seed_markets`, `seed_zap_scan_user`.
- Listings: `fetch_listings`, `fetch_hud` (`--state`, `--zip`), `import_csv` (user_email, properties_csv, rental/expense CSV options), `rescreen_pipeline`.
- VRM (VA REO): `collect_vrm_data` (state), `enrich_vrm_details` (state, force flag), `import_vrm_json` (JSON path).
- Other REO and foreclosure sources: `collect_fannie_mae` (location, request id, all pending), `ingest_hud_reo` and `ingest_usda_reo` (fixture flag, URL override), `fetch_hud_source_index` (output dir, local HTML), `fetch_attom_preforeclosure` (ZIP, radius, dry-run), `scrape_dallas_county_nts` (dry-run).
- Market data: `populate_growth_areas` (state/city pairs, file, force, list), `refresh_market_data` (ZIPs, state, force), `update_market_indicators` (optional metro).

## Invariants
- Cache-aware commands skip data fresher than 30 days unless the force flag is given (help text in `refresh_market_data`, `populate_growth_areas`).
- State arguments are 2-letter codes.
- Commands with a dry-run flag (`fetch_attom_preforeclosure`, `scrape_dallas_county_nts`) must not save.

## Side Effects
- Write to the database (Listing, VrmProperty, GrowthArea, MarketSnapshot, DiscoveryRequest, pipeline records and others).
- Make HTTP calls to external sources (HUD, USDA, Fannie Mae HomePath, VRM, ATTOM, Census, BLS, FRED) except in fixture mode.
- `fetch_hud_source_index` writes snapshot and diff files to an output directory.

## Verification
- Run: `.venv/bin/python -m pytest <paths>` (configured by `pytest.ini`)
