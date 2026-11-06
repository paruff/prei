# Listing and Foreclosure Sources

## Overview
Source adapters for listing ingestion; `fetch()` returns normalized dicts (see `__init__.py` docstring).

## Interface
- `attom_adapter.py`: `ATTOMAdapter`, `ATTOMAPIError`, `ATTOMAuthenticationError`, `ATTOMRateLimitError`, `fetch(location)`.
- `attom_preforeclosure.py`: `fetch_attom_preforeclosure`, `DEFAULT_RADIUS`.
- `reso_adapter.py`: `RESOAdapter`, `RESOAPIError`, `RESOAuthenticationError`, `RESORateLimitError`, `normalize_property_type`, `normalize_property_data`.
- `fred_adapter.py`: `FREDAdapter`, `FREDAPIError`, `FREDAuthenticationError`, `create_fred_adapter`.
- `hud_scraper.py`: `HUDHomeScraper`, `HUDScraperError`, `HUDWebsiteChangeError`, `fetch(state_code)`. `hud_source_index.py`: `fetch_hud_homes_for_sale_html`, `compute_content_hash`, `canonicalize_url`, `discover_hud_homes_for_sale_sources`, `diff_source_indexes`, `HUDSourceIndexFetchError`.
- `vrm_scraper.py`: `VrmScraper`. `vrm_json_importer.py`: `parse_vrm_json_record`, `upsert_vrm_records`. `fannie_mae.py`: `FannieMaeHomePathClient`. `dummy_adapter.py`: `fetch()`.

## Invariants
- Money fields normalize to `Decimal`; ATTOM cost per call defaults to `ATTOM_COST_PER_CALL` (0.01).
- `upsert_vrm_records` writes normalized records to the database.

## Side Effects
- HTTP to ATTOM, RESO, FRED, HUD, VRM, Fannie Mae; cache use; DB writes in `vrm_json_importer`; reads `ATTOM_API_KEY`, `ATTOM_DEFAULT_RADIUS`, `FRED_API_KEY`, `RESO_*`.

## Verification
- Run: `.venv/bin/python -m pytest core/tests/test_attom_adapter.py core/tests/test_hud_scraper.py` (pytest.ini)
