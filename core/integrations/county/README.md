# County Foreclosure Scrapers

## Overview
Texas county notice-of-trustee-sale (NTS) and sheriff-sale scrapers returning lists of notice dicts.

## Interface
- `tx_base.py`: `scrape_county_nts(county_config)` (Playwright fetch, HTML table parse), `REQUEST_TIMEOUT = 30`, `TEXAS_STATE`.
- `dallas_tx.py`: `scrape_dallas_county_nts()`, `DallasNTSRecord`, `SELECTORS`, `ALT_SELECTORS`, `COLUMNS`.
- `tx_sheriff.py`: `SHERIFF_COUNTIES`, `scrape_sheriff_sales(county_name)`, `scrape_all_sheriff_sales()`.
- `bexar_tx.py`, `collin_tx.py`, `denton_tx.py`, `el_paso_tx.py`, `fort_bend_tx.py`, `harris_tx.py`, `hidalgo_tx.py`, `montgomery_tx.py`, `tarrant_tx.py`, `travis_tx.py`: each exposes `COUNTY`, `ENDPOINT`, `SELECTORS` and `scrape() -> list[dict]` delegating to `scrape_county_nts`.

## Invariants
- Bid amounts parse to `Decimal` (`_parse_bid`, `_parse_opening_bid`); unparseable values yield `None`.
- Per-county modules hold config only; parsing logic lives in `tx_base.py` (Dallas has its own parser).

## Side Effects
- Network requests (Playwright browser or HTTP) to county clerk sites; Dallas applies `DEFAULT_DELAY` between requests.

## Verification
- Run: `.venv/bin/python -m pytest tests core/tests -k "county or sheriff or dallas"` (pytest.ini)
