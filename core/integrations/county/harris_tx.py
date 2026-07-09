"""Harris County (Houston) TX NTS scraper, powered by Playwright."""

from core.integrations.county.tx_base import scrape_county_nts

COUNTY = "Harris"
ENDPOINT = "https://www.harriscountyclerk.com/foreclosures"
SELECTORS = {
    "table": "table.foreclosure-table",
    "alt_tables": [
        "table#foreclosures",
        "table.table-striped",
        "div.foreclosure-list table",
    ],
}


def scrape() -> list[dict]:
    """Scrape Harris County NTS notices."""
    return scrape_county_nts(
        {
            "county_name": COUNTY,
            "endpoint": ENDPOINT,
            "selectors": SELECTORS,
        }
    )
