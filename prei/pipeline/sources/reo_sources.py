"""Real REO (Real Estate Owned) property discovery sources.

Adapters that query live APIs from Fannie Mae HomePath, HUD Homestore,
VA Foreclosures, and USDA Foreclosures.

Each adapter gracefully handles API unavailability (connection errors,
rate limits, 5xx responses) by returning empty lists — never crashing.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Set

import requests

from prei.pipeline.handlers.discovery import DiscoverySanitizer
from prei.pipeline.sources.base import DiscoverySource

logger = logging.getLogger(__name__)

USER_AGENT = "PREI/0.2 (passive-investor-tool; mailto:bot@prei.dev)"
TIMEOUT = 15
MAX_RETRIES = 2
BACKOFF_SECONDS = 2

# Explicit key → property mapping cache per address hash
_seen_hashes: Set[str] = set()


def _request_with_retry(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    method: str = "GET",
    json_body: Optional[Dict[str, Any]] = None,
) -> Optional[requests.Response]:
    default_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        default_headers.update(headers)

    for attempt in range(1 + MAX_RETRIES):
        try:
            if method == "POST":
                resp = requests.post(
                    url,
                    json=json_body,
                    params=params,
                    headers=default_headers,
                    timeout=TIMEOUT,
                )
            else:
                resp = requests.get(
                    url,
                    params=params,
                    headers=default_headers,
                    timeout=TIMEOUT,
                )
            if resp.status_code in (200, 204):
                return resp
            if resp.status_code in (429, 503):
                logger.warning(
                    "%s returned %d — backing off %ds",
                    url,
                    resp.status_code,
                    BACKOFF_SECONDS * (attempt + 1),
                )
                time.sleep(BACKOFF_SECONDS * (attempt + 1))
                continue
            logger.info("%s returned %d — skipping", url, resp.status_code)
            return None
        except requests.RequestException as exc:
            logger.warning("%s request failed (attempt %d): %s", url, attempt + 1, exc)
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_SECONDS * (attempt + 1))
    return None


def _normalize_homepath(property_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map Fannie Mae HomePath API response to pipeline-compatible dict."""
    address = property_data.get("address", property_data.get("fullAddress", ""))
    return {
        "id": f"fm-{property_data.get('propertyId', property_data.get('id', ''))}",
        "address": address,
        "price": property_data.get("price"),
        "beds": property_data.get("bedrooms", property_data.get("beds")),
        "baths": property_data.get("bathrooms", property_data.get("baths")),
        "sqft": property_data.get("squareFeet", property_data.get("sqft")),
        "year_built": property_data.get("yearBuilt"),
        "source_url": property_data.get("url", ""),
    }


class FannieMaeSource(DiscoverySource):
    """Live Fannie Mae HomePath API source.

    Queries the HomePath property search endpoint for REO listings
    by state and optional ZIP code.

    API endpoint: https://www.homepath.com/api/search
    Requires: no API key (public property search)
    """

    API_URL = "https://www.homepath.com/api/search"

    @property
    def name(self) -> str:
        return "fannie_mae"

    def fetch(
        self,
        state: str,
        zip_code: Optional[str] = None,
        limit: int = 50,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        state = state.strip().upper()[:2]

        payload: Dict[str, Any] = {
            "state": state,
            "pageSize": min(limit, 100),
            "sortBy": "price",
            "sortOrder": "asc",
        }
        if zip_code:
            payload["zipcode"] = zip_code

        headers = {
            "Content-Type": "application/json",
            "Origin": "https://www.homepath.com",
            "Referer": "https://www.homepath.com/",
        }

        logger.info("Fannie Mae: querying %s for state=%s", self.API_URL, state)
        resp = _request_with_retry(
            self.API_URL,
            headers=headers,
            method="POST",
            json_body=payload,
        )
        if resp is None:
            return []

        try:
            data = resp.json()
        except (ValueError, TypeError):
            logger.warning("Fannie Mae: invalid JSON response")
            return []

        results = (
            data.get("results") or data.get("properties") or data.get("data") or []
        )
        listing_list = results if isinstance(results, list) else []

        listings = []
        seen_ids: Set[str] = set()
        for prop in listing_list:
            mapped = _normalize_homepath(prop)
            if mapped["id"] in seen_ids:
                continue
            seen_ids.add(mapped["id"])
            dedup_addr = DiscoverySanitizer.clean_address(mapped["address"])
            dedup_hash = DiscoverySanitizer.compute_address_hash(dedup_addr)
            if dedup_hash in _seen_hashes:
                continue
            _seen_hashes.add(dedup_hash)
            listings.append(mapped)

        logger.info(
            "Fannie Mae: %d/%d results after dedup for %s",
            len(listings),
            len(listing_list),
            state,
        )
        return listings[:limit]


class HUDHomestoreSource(DiscoverySource):
    """Live HUD Homestore government foreclosure source.

    Queries the HUD Homestore property search API for HUD-owned
    properties (FHA-insured foreclosures).

    API endpoint: https://www.hudhomestore.com/Listing/PropertySearch
    Requires: no API key (public search)
    """

    API_URL = "https://www.hudhomestore.com/Listing/PropertySearch"

    @property
    def name(self) -> str:
        return "hud"

    def fetch(
        self,
        state: str,
        zip_code: Optional[str] = None,
        limit: int = 50,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        state = state.strip().upper()[:2]
        params = {"state": state, "pageSize": min(limit, 100)}
        if zip_code:
            params["zip"] = zip_code

        headers = {
            "Referer": "https://www.hudhomestore.com/",
            "X-Requested-With": "XMLHttpRequest",
        }

        logger.info("HUD: querying %s for state=%s", self.API_URL, state)
        resp = _request_with_retry(self.API_URL, params=params, headers=headers)
        if resp is None:
            return []

        try:
            data = resp.json()
        except (ValueError, TypeError):
            return []

        results = (
            data.get("results") or data.get("data") or data.get("properties") or []
        )
        listing_list = results if isinstance(results, list) else []

        listings = []
        for prop in listing_list:
            mapped = {
                "id": f"hud-{prop.get('caseNumber', prop.get('id', ''))}",
                "address": prop.get("displayAddress", prop.get("address", "")),
                "price": prop.get("currentPrice", prop.get("price")),
                "beds": prop.get("bedrooms", prop.get("beds")),
                "baths": prop.get("bathrooms", prop.get("baths")),
                "sqft": prop.get("squareFootage", prop.get("sqft")),
                "status": prop.get("listingStatus"),
            }
            listings.append(mapped)

        logger.info("HUD: %d results for %s", len(listings), state)
        return listings[:limit]


class VAForeclosuresSource(DiscoverySource):
    """Live VA foreclosure source.

    Queries the VA foreclosed property listing system for vendee-eligible
    and publicly available VA foreclosures.

    API endpoint: https://www.homestore.va.gov/Listing/PropertySearch
    Requires: no API key
    """

    API_URL = "https://www.homestore.va.gov/Listing/PropertySearch"

    @property
    def name(self) -> str:
        return "va"

    def fetch(
        self,
        state: str,
        zip_code: Optional[str] = None,
        limit: int = 50,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        state = state.strip().upper()[:2]
        params = {"stateCode": state, "pageSize": min(limit, 100)}
        if zip_code:
            params["zip"] = zip_code

        logger.info("VA: querying %s for state=%s", self.API_URL, state)
        resp = _request_with_retry(self.API_URL, params=params)
        if resp is None:
            return []

        try:
            data = resp.json()
        except (ValueError, TypeError):
            return []

        results = (
            data.get("data") or data.get("properties") or data.get("results") or []
        )
        listing_list = results if isinstance(results, list) else []

        listings = []
        for prop in listing_list:
            mapped = {
                "id": f"va-{prop.get('propertyNumber', prop.get('id', ''))}",
                "address": f"{prop.get('street', '')} {prop.get('city', '')} {prop.get('state', '')}".strip(),
                "price": prop.get("listPrice", prop.get("price")),
                "beds": prop.get("bedrooms", prop.get("beds")),
                "baths": prop.get("bathrooms", prop.get("baths")),
            }
            listings.append(mapped)

        logger.info("VA: %d results for %s", len(listings), state)
        return listings[:limit]


class USDAForeclosuresSource(DiscoverySource):
    """Live USDA Rural Development foreclosure source.

    Queries USDA single-family housing foreclosure listings.

    API endpoint: https://www.sc.egov.usda.gov/data/...
    Requires: no API key
    """

    API_URL = "https://www.sc.egov.usda.gov/data/sfh/PropertyForSaleServlet"

    @property
    def name(self) -> str:
        return "usda"

    def fetch(
        self,
        state: str,
        zip_code: Optional[str] = None,
        limit: int = 50,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        state = state.strip().upper()[:2]
        params: Dict[str, Any] = {"state": state}
        if zip_code:
            params["zip"] = zip_code

        logger.info("USDA: querying %s for state=%s", self.API_URL, state)
        resp = _request_with_retry(self.API_URL, params=params)
        if resp is None:
            return []

        try:
            data = resp.json()
        except (ValueError, TypeError):
            return []

        results = (
            data.get("properties") or data.get("results") or data.get("data") or []
        )
        listing_list = results if isinstance(results, list) else []

        listings = []
        for prop in listing_list:
            mapped = {
                "id": f"usda-{prop.get('propertyId', prop.get('id', ''))}",
                "address": prop.get("address", ""),
                "price": prop.get("listPrice", prop.get("price")),
                "beds": prop.get("bedrooms"),
                "baths": prop.get("bathrooms"),
            }
            listings.append(mapped)

        logger.info("USDA: %d results for %s", len(listings), state)
        return listings[:limit]
