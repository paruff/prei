# core/services/sources

## Overview
Discovery-stage data source adapters. Each adapter fetches raw listing dicts for a US state (optionally a ZIP) from an external feed, scrape, or file, in a shape accepted by `DiscoverySanitizer.transform_input()` (see [../discovery.py](../discovery.py)). A registry maps source names to adapter classes.

## Interface
- `base.py`: `DiscoverySource` (ABC) with abstract `name` property and `fetch(state, zip_code=None, **kwargs) -> list[dict]`.
- `registry.py`: `list_sources()`, `get_source(name, **kwargs)`, `discover_from_all(state, zip_code, source_filter, **kwargs)`; built-in names in `_BUILTIN_SOURCES`: `fannie_mae`, `hud`, `va`, `usda`, `county_tx`, `vrm`.
- `reo_sources.py`: `FannieMaeSource`, `HUDHomestoreSource`, `VAForeclosuresSource`, `USDAForeclosuresSource`; helpers `_request_with_retry`, `_normalize_homepath`; constants `USER_AGENT`, `TIMEOUT`, `MAX_RETRIES`, `BACKOFF_SECONDS`.
- `county.py`: `TexasCountyForeclosureSource`, `FloridaCountyForeclosureSource`, feed tables `TEXAS_COUNTY_FEEDS`, `FLORIDA_COUNTY_FEEDS`, `_fetch_via_playwright`.
- `file_source.py`: `CsvFileSource`, `JsonFileSource`, `DEFAULT_COLUMN_MAP` (not registered in `_BUILTIN_SOURCES`).
- `vrm_source.py`: `VrmDiscoverySource`.

## Invariants
- `get_source` raises `ValueError` for names not in `_BUILTIN_SOURCES` (`registry.py:get_source`).
- `discover_from_all` never raises for a failing source: it logs the error and returns `[]` for that name (`registry.py:discover_from_all`).
- `FloridaCountyForeclosureSource` is not in the registry (only `county_tx` is).
- Adapters return raw dicts; no persistence is done here by the HTTP/file adapters.

## Side Effects
- Network: `requests.get`/`requests.post` with retry/backoff (`reo_sources.py:_request_with_retry`), `requests.get` in `county.py`, optional Playwright browser fetch (`county.py:_fetch_via_playwright`).
- Disk read: `CsvFileSource` opens `file_path` (`file_source.py`).
- `vrm_source.py` does `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "investor_app.settings")` and reads the Django ORM.
- Logging via `logging.getLogger(__name__)`.

## Verification
- Run: `.venv/bin/python -m pytest tests/test_discovery.py tests/test_discovery_integration.py` (config in `pytest.ini`)
