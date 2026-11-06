# Market Data Adapters

## Overview
Per-metric adapters (rent, schools, walkability, comps, crime, demographics, employment, HUD FMR/income limits, market trends). Each tries a live API and returns `None`/`[]` on failure. Overview and env vars are in [../README.md](../README.md).

## Interface
- `rents.py`: `fetch_rent_estimate`, `get_rent_estimate_for_listing` (dummy). `schools.py`: `fetch_school_rating`, `get_school_rating`. `walkscore.py`: `fetch_walk_score`. `comps.py`: `fetch_comps_for_listing`, `get_comps_for_listing`. `crime.py`: `get_crime_score` (dummy only).
- `census.py`: `fetch_zip_demographics`, `fetch_place_growth_metrics`, `discover_places_in_state`, `compute_supply_constraint_index`, `fetch_housing_demand_index`, `get_acs_vintages`, `STATE_FIPS`.
- `bls.py`: `fetch_unemployment_rate`, `fetch_employment_growth`. `bls_laus.py`: `fetch_county_unemployment`, `fetch_county_employment`. `bls_qcew.py` / `qcew_adapter.py`: `fetch_county_employment_growth`.
- `hud_fmr.py`: `FMRClient`, `FMRError`, `get_rent_estimate`. `hud_il.py`: `ILClient`, `ILError`, `fetch_area_median_income`. `fmr_adapter.py`: `fetch_fmr_entity_id`, `fetch_fmr_data`. `rentometer.py`: `RentometerClient`, `RentometerError`, `get_rent_estimate`.
- `market_trends.py`: `MarketIndicatorData`, `classify_market_health`, `fetch_market_indicators`, `get_indicator_history`, `build_sparkline_points`, `get_latest_indicators`, `update_market_indicators`, `get_market_health_summary`.
- `city_zip_map.py`: `lookup_city_zip`; `county_fips_map.py`: `lookup_county_fips`.

## Invariants
- Rates and rents are `Decimal`; cache TTLs: RentCast 7 days, GreatSchools 30 days.
- `crime.py` never calls a live API (DECISION-2).

## Side Effects
- HTTP to RentCast, GreatSchools, Walk Score, ATTOM, Census, BLS, HUD; Django cache use; reads `ATTOM_API_KEY` in `comps.py`.

## Verification
- Run: `.venv/bin/python -m pytest tests/test_market_adapters.py tests/test_market_adapters_comps_wiring.py core/tests/test_market_adapters_v2.py` (pytest.ini)
