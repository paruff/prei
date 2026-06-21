import hashlib
import json
import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

import requests
from django.core.cache import cache

from core.models import Listing


logger = logging.getLogger(__name__)

RENTCAST_API_BASE = "https://api.rentcast.io/v1/rent/long-term"
RENTCAST_CACHE_TTL = 604800       # 7 days
RENTCAST_DAILY_BUDGET = 100        # free tier limit


def get_rent_estimate_for_listing(listing: Listing) -> Decimal:
    """Return a dummy monthly rent estimate using PPSF * 0.9 as heuristic."""
    if not listing.sq_ft:
        return Decimal("0")
    ppsf = Decimal(listing.price) / Decimal(listing.sq_ft)
    monthly = (ppsf * Decimal("0.9")).quantize(Decimal("0.01"))
    return monthly


def fetch_rent_estimate(
    address: str,
    api_key: str,
    zip_code: str | None = None,
) -> Decimal | None:
    """Fetch a rental estimate from the RentCast API.

    Args:
        address: Property street address.
        api_key: RentCast API key (free at https://rentcast.io).
        zip_code: Optional ZIP code for disambiguation.

    Returns:
        Decimal monthly rent estimate, or None on any error.
    """
    if not api_key:
        logger.warning("RentCast API key not provided")
        return None

    cache_key = f"rentcast_rent_{hashlib.md5(address.encode()).hexdigest()}"

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    counter_key = f"rentcast_calls_{date.today().isoformat()}"
    today_count = cache.get_or_set(counter_key, 0, timeout=86400)
    if today_count >= RENTCAST_DAILY_BUDGET:
        logger.warning("RentCast daily budget exhausted (%s calls)", today_count)
        return None

    url = f"{RENTCAST_API_BASE}?address={quote(address)}&propertyType=SingleFamily"
    if zip_code:
        url += f"&zipCode={zip_code}"

    try:
        resp = requests.get(url, headers={"X-Api-Key": api_key}, timeout=10)
        resp.raise_for_status()
        resp_json = resp.json()
        rent = resp_json["data"]["rent"]
        result = Decimal(str(rent)).quantize(Decimal("0.01"))
    except (
        requests.RequestException,
        KeyError,
        json.JSONDecodeError,
        TypeError,
        InvalidOperation,
    ) as exc:
        logger.warning("RentCast API error for address=%s: %s", address, exc)
        return None

    cache.set(counter_key, today_count + 1, timeout=86400)
    cache.set(cache_key, result, timeout=RENTCAST_CACHE_TTL)
    return result
