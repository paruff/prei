"""Texas county sheriff sale scraper — upcoming foreclosure auctions.

Each TX county sheriff publishes upcoming sale calendars.  These are
typically monthly lists of properties scheduled for auction.

URL patterns are consistent: {county_name}countyso.org or similar.
The scraper uses Playwright to render the page and parse the table.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any

from core.integrations.county.tx_base import scrape_county_nts

logger = logging.getLogger("prei.scraper.sheriff")

SHERIFF_COUNTIES = [
    {
        "county_name": "Harris",
        "endpoint": "https://www.harriscountyso.org/Public/RealAuctions",
        "selectors": {
            "table": "table.auction-table",
            "alt_tables": ["table#auctions", "table.table-striped", "div.auction-list table"],
        },
    },
    {
        "county_name": "Dallas",
        "endpoint": "https://www.dallascounty.org/departments/sheriff/civil-enforcement/civil-sales.php",
        "selectors": {
            "table": "table.sales-table",
            "alt_tables": ["table#civil-sales", "table.table-striped"],
        },
    },
    {
        "county_name": "Travis",
        "endpoint": "https://www.traviscountytx.gov/sheriff/civil-district/foreclosure-sales",
        "selectors": {
            "table": "table.foreclosure-table",
            "alt_tables": ["table#foreclosures", "table.table-striped", "div.foreclosure-list table"],
        },
    },
    {
        "county_name": "Bexar",
        "endpoint": "https://www.bexar.org/1568/Sheriffs-Office-Constable-Sales",
        "selectors": {
            "table": "table.sales-table",
            "alt_tables": ["table#sheriff-sales", "table.table-striped"],
        },
    },
    {
        "county_name": "Tarrant",
        "endpoint": "https://www.tarrantcountytx.gov/sheriff/civil-enforcement/foreclosure-sales",
        "selectors": {
            "table": "table.foreclosure-table",
            "alt_tables": ["table#foreclosures", "div.foreclosure-list table"],
        },
    },
]


def scrape_sheriff_sales(county_name: str) -> list[dict[str, Any]]:
    """Scrape sheriff sale notices for a specific county."""
    config = next(
        (c for c in SHERIFF_COUNTIES if c["county_name"].lower() == county_name.lower()),
        None,
    )
    if not config:
        logger.warning("Sheriff scraper: no config for %s", county_name)
        return []
    return scrape_county_nts(config)


def scrape_all_sheriff_sales() -> dict[str, list[dict[str, Any]]]:
    """Scrape sheriff sale notices for all configured counties."""
    results: dict[str, list[dict[str, Any]]] = {}
    for config in SHERIFF_COUNTIES:
        county = config["county_name"]
        logger.info("Sheriff scraper: starting %s County", county)
        notices = scrape_county_nts(config)
        results[county] = notices
        logger.info("Sheriff scraper: %s County → %d notices", county, len(notices))
    return results
