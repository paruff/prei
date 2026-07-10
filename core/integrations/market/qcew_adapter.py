"""BLS QCEW county-level employment growth adapter.

Replaces FRED state-level employment data with actual county employment
figures from the Bureau of Labor Statistics Quarterly Census of Employment
and Wages (QCEW).

No API key required — free public data at data.bls.gov/cew/.

Data source: https://data.bls.gov/cew/data/api/{year}/a/area/{fips_code}.csv

Key fields:
  - oty_annual_avg_emplvl_pct_chg: over-the-year employment change (percent)
  - own_code=0: total all ownerships
  - industry_code=10: total all industries
  - agglvl_code=70: county level, total covered
"""

from __future__ import annotations

import csv
import io
import logging
from decimal import Decimal

import requests

logger = logging.getLogger(__name__)

QCEW_BASE = "https://data.bls.gov/cew/data/api"
REQUEST_TIMEOUT = 15


def fetch_county_employment_growth(
    county_fips: str,
    year: int = 2024,
) -> Decimal | None:
    """Fetch over-the-year employment growth for a county from BLS QCEW.

    Args:
        county_fips: 5-character county FIPS code (e.g. ``"48113"`` for Dallas TX).
        year: Data year.  Use prior year if current year not yet published.

    Returns:
        Employment growth rate as a Decimal fraction (e.g. ``Decimal("0.023")``
        for 2.3% growth).  Returns ``None`` if data is unavailable or suppressed.
    """
    url = f"{QCEW_BASE}/{year}/a/area/{county_fips}.csv"

    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning(
            "QCEW request failed for FIPS %s year %d: %s",
            county_fips,
            year,
            exc,
        )
        return None

    reader = csv.DictReader(io.StringIO(resp.text))

    for row in reader:
        own = row.get("own_code", "").strip()
        ind = row.get("industry_code", "").strip()
        agglvl = row.get("agglvl_code", "").strip()
        disclosure = row.get("disclosure_code", "").strip()

        # Total all ownerships, total all industries, county level, not suppressed
        if own == "0" and ind == "10" and agglvl == "70" and disclosure != "N":
            pct_chg = row.get("oty_annual_avg_emplvl_pct_chg", "").strip()
            if pct_chg and pct_chg not in ("", "0", "0.0"):
                try:
                    # Value is a percentage (e.g. "2.3" = 2.3%)
                    return Decimal(pct_chg) / Decimal("100")
                except ValueError, TypeError:
                    return None

    logger.info(
        "QCEW: no matching row for FIPS %s year %d",
        county_fips,
        year,
    )
    return None
