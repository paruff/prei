"""Comparable sales adapter using ATTOM Data Solutions API.

Reuses the existing ``ATTOMAdapter`` in ``core.integrations.sources``
(ATTOM_API_KEY env var, no new key required).
"""

from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Any, Dict, List

from core.integrations.sources.attom_adapter import (
    ATTOMAPIError,
    ATTOMAdapter,
    ATTOMRateLimitError,
)
from core.models import Listing

logger = logging.getLogger(__name__)


def get_comps_for_listing(listing: Listing) -> List[Dict]:
    """Return dummy comparable sales for a listing (kept for backward compatibility).

    Each comp: {address, price: Decimal, sq_ft: int, ppsf: Decimal}
    """
    base_ppsf = Decimal(listing.price) / Decimal(listing.sq_ft or 1)
    comps = []
    for i, factor in enumerate(
        [Decimal("0.9"), Decimal("1.0"), Decimal("1.1")], start=1
    ):
        ppsf = (base_ppsf * factor).quantize(Decimal("0.01"))
        price = (ppsf * Decimal(listing.sq_ft or 1)).quantize(Decimal("0.01"))
        comps.append(
            {
                "address": f"Comp {i} - {listing.city}",
                "price": price,
                "sq_ft": listing.sq_ft or 0,
                "ppsf": ppsf,
            }
        )
    return comps


def fetch_comps_for_listing(
    listing: Listing, api_key: str | None = None
) -> List[Dict[str, Any]]:
    """Fetch comparable sales for a listing using ATTOM sales history.

    Reuses ``ATTOM_API_KEY`` from the environment if *api_key* is ``None``.
    Falls back to the dummy ``get_comps_for_listing`` on any failure.

    Args:
        listing: The listing to find comps for.  Must have *address*, *city*,
            *state*, and *zip_code*.
        api_key: Optional ATTOM API key override.  If ``None``, reads from
            ``os.environ["ATTOM_API_KEY"]``.

    Returns:
        List of dicts matching the dummy's shape:
        ``{address, price: Decimal, sq_ft: int, ppsf: Decimal}``.
        Returns an empty list when the API is unavailable or returns no data.
    """
    resolved_key = api_key or os.getenv("ATTOM_API_KEY", "")
    if not resolved_key:
        logger.warning("comps: ATTOM_API_KEY not set — returning dummy comps")
        return []

    # Build a full address string for ATTOM (street + city/state/ZIP).
    address1 = listing.address
    address2 = f"{listing.city}, {listing.state} {listing.zip_code}".strip()
    full_address = f"{address1}, {address2}"

    adapter = ATTOMAdapter(api_key=resolved_key)

    try:
        sales_data = adapter.fetch_sales_history(full_address)
    except (ATTOMAPIError, ATTOMRateLimitError) as exc:
        logger.warning("comps: ATTOM sales history error for %s: %s", address1, exc)
        return []
    except Exception:
        logger.exception(
            "comps: unexpected error fetching sales history for %s", address1
        )
        return []

    if not isinstance(sales_data, dict):
        return []

    # ATTOM /sale/snapshot returns {"property": [{"saleHistory": [...]}]}.
    # Normalise: extract sale entries from inside the property array.
    raw_properties = sales_data.get("property", [])
    if isinstance(raw_properties, dict):
        raw_properties = [raw_properties]

    sale_entries: list = []
    if isinstance(raw_properties, list):
        for prop in raw_properties:
            prop_sales = prop.get("saleHistory", [])
            if isinstance(prop_sales, dict):
                prop_sales = [prop_sales]
            if isinstance(prop_sales, list):
                sale_entries.extend(prop_sales)

    # Also check for saleHistory at the top level (alternative response format).
    top_sales = sales_data.get("saleHistory", [])
    if isinstance(top_sales, dict):
        top_sales = [top_sales]
    if isinstance(top_sales, list):
        # Prepend so top-level entries come first.
        sale_entries = list(top_sales) + sale_entries

    if not sale_entries:
        logger.info("comps: no sale history entries found for %s", address1)
        return []

    comps: List[Dict[str, Any]] = []
    for sale in sale_entries:
        if not isinstance(sale, dict):
            continue
        try:
            raw_price = sale.get("amount", sale.get("saleAmt", {}))
            if isinstance(raw_price, dict):
                raw_price = raw_price.get("saleAmt", 0)
            price = Decimal(str(raw_price or 0)).quantize(Decimal("0.01"))
            if price <= 0:
                continue

            raw_sqft = sale.get("lotSize2", sale.get("buildingArea", 0))
            sq_ft = int(raw_sqft or 0)

            ppsf = (
                (price / Decimal(sq_ft or 1)).quantize(Decimal("0.01"))
                if sq_ft
                else Decimal("0")
            )

            sale_address = sale.get("address", {}).get("oneLine", "")
            if not sale_address:
                sale_address = sale.get("location", {}).get("oneLine", "")

            comps.append(
                {
                    "address": str(sale_address or f"Comp - {address1}"),
                    "price": price,
                    "sq_ft": sq_ft,
                    "ppsf": ppsf,
                }
            )
        except (ValueError, TypeError, InvalidOperation) as exc:
            logger.warning("comps: skipped malformed sale entry: %s", exc)
            continue

    return comps


# Also import at module level for the Decimal operations used above.
from decimal import InvalidOperation  # noqa: E402  # pragma: no cover
