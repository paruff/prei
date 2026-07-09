"""Tarrant County (Fort Worth) TX NTS scraper, powered by Playwright."""

from core.integrations.county.tx_base import scrape_county_nts

COUNTY = "Tarrant"
ENDPOINT = "https://www.tarrantcounty.com/en/county-clerk/foreclosures.html"
SELECTORS = {
    "table": "table.foreclosure-table",
    "alt_tables": [
        "table#foreclosures",
        "table.table-striped",
        "div.foreclosure-list table",
    ],
}


def scrape() -> list[dict]:
    """Scrape Tarrant County NTS notices."""
    return scrape_county_nts(
        {
            "county_name": COUNTY,
            "endpoint": ENDPOINT,
            "selectors": SELECTORS,
        }
    )
