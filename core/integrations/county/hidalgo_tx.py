"""Hidalgo County (McAllen) TX NTS scraper, powered by Playwright."""

from core.integrations.county.tx_base import scrape_county_nts

COUNTY = "Hidalgo"
ENDPOINT = "https://www.hidalgocounty.us/262/County-Clerk"
SELECTORS = {
    "table": "table.foreclosure-table",
    "alt_tables": [
        "table#foreclosures",
        "table.table-striped",
        "div.foreclosure-list table",
    ],
}


def scrape() -> list[dict]:
    """Scrape Hidalgo County NTS notices."""
    return scrape_county_nts(
        {
            "county_name": COUNTY,
            "endpoint": ENDPOINT,
            "selectors": SELECTORS,
        }
    )
