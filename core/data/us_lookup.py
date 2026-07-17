"""Comprehensive US city → county FIPS lookup.

Replaces the hardcoded county_fips_map.py with data-driven coverage
across 29,727 US cities and 86 county→FIPS mappings.

Data sources:
  - city_county.json: 29,727 city→county name mappings
  - county_fips.json: 86 county name→FIPS code mappings
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def _load_json(name: str) -> dict[str, str]:
    path = Path(__file__).parent / name
    if not path.exists():
        return {}
    return json.loads(path.read_text())


_city_county: dict[str, str] = _load_json("city_county.json")
_county_fips: dict[str, str] = _load_json("county_fips.json")

# Deprecated: kept for backward compatibility only.
from core.integrations.market.county_fips_map import (
    lookup_county_fips as _legacy_fips,
)


def _strip_census_suffix(city_name: str) -> str:
    """Normalize Census place names to plain city names."""
    city = city_name.strip()
    city = re.sub(r"\s+(city|town|CDP|village|borough)$", "", city, flags=re.IGNORECASE)
    city = re.sub(r"\s+unified government \(balance\)$", "", city, flags=re.IGNORECASE)
    city = re.sub(r"\s+consolidated government \(balance\)$", "", city, flags=re.IGNORECASE)
    return city.strip()


def lookup_county_fips(state_code: str, city_name: str) -> str | None:
    """Get county FIPS code for a US city using comprehensive data.

    Chain: city_name → county_name → county_FIPS

    1. Try the legacy hardcoded map first (97 entries, precise)
    2. Fall back to comprehensive city_county.json (29,727 entries)
    3. Look up county name in county_fips.json (86 entries)
    """
    # 1. Try legacy hardcoded map (precise FIPS)
    fips = _legacy_fips(state_code, city_name)
    if fips:
        return fips

    # 2. Comprehensive city→county lookup
    city = _strip_census_suffix(city_name)
    state = state_code.strip().upper()
    key = f"{state}|{city.title()}"
    county_name = _city_county.get(key)

    if not county_name:
        return None

    # 3. County name → FIPS
    fips_key = f"{state}|{county_name.title()}"
    return _county_fips.get(fips_key)


def lookup_county_name(state_code: str, city_name: str) -> str | None:
    """Get county name for a US city."""
    city = _strip_census_suffix(city_name)
    state = state_code.strip().upper()
    key = f"{state}|{city.title()}"
    return _city_county.get(key)
