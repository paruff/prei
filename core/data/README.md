# core/data

## Overview
Static US city to county to FIPS lookup data and its accessor module.

## Interface
- `us_lookup.lookup_county_fips(state_code, city_name) -> str | None`
- `us_lookup.lookup_county_name(state_code, city_name) -> str | None`
- Data files: `city_county.json` (city to county name), `county_fips.json` (county name to FIPS).

## Invariants
- JSON files load once at import (`_city_county`, `_county_fips`); a missing file yields `{}`, not an error.
- Census suffixes such as "city" or "CDP" are stripped before lookup (`_strip_census_suffix`).
- Falls back to the legacy `core.integrations.market.county_fips_map.lookup_county_fips`.

## Side Effects
- Reads the JSON files from disk at import time only.

## Verification
- Run: `.venv/bin/python -m pytest <paths>` (configured by `pytest.ini`)
