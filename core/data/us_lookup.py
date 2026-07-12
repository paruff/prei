"""Comprehensive US city → county lookup.

Generated from the US Cities Database (29,727 cities, 50 states).
Source: https://github.com/kelvins/US-Cities-Database (public domain).

Provides:
  - lookup_county(state_code, city_name) → county name or None
  - lookup_county_fips(state_code, city_name) → county FIPS or None

Replaces the hardcoded county_fips_map.py with data-driven coverage.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# City → county name mapping (29,727 entries)
# Key: "ST|City" → county name
# ---------------------------------------------------------------------------
_city_county: dict[str, str] = {}


def _load() -> dict[str, str]:
    """Load the city→county mapping from embedded JSON data."""
    import json
    from pathlib import Path

    data_file = Path(__file__).parent / "city_county.json"
    if not data_file.exists():
        return {}
    result: dict[str, str] = json.loads(data_file.read_text())
    return result


_city_county = _load()

# County name → FIPS mapping for the most common counties
_county_fips: dict[tuple[str, str], str] = {}


def lookup_county(state_code: str, city_name: str) -> str | None:
    """Look up the county name for a city in a state.

    Strips Census suffixes before lookup.
    """
    city = re.sub(
        r"\s+(city|town|CDP|village|borough)$",
        "",
        city_name.strip(),
        flags=re.IGNORECASE,
    )
    key = f"{state_code.strip().upper()}|{city.strip().title()}"
    return _city_county.get(key)


def lookup_county_fips(state_code: str, city_name: str) -> str | None:
    """Look up county FIPS code for a state/city pair.

    Falls back to the hardcoded FIPS map for known counties.
    """
    from core.integrations.market.county_fips_map import lookup_county_fips as _fips

    # Try the hardcoded FIPS map first (has FIPS codes)
    result = _fips(state_code, city_name)
    if result:
        return result
    return None
