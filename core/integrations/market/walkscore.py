"""Walk Score API adapter for walk/transit/bike scores."""
import hashlib
import json
import logging
from typing import Any
from urllib.parse import quote

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

WALKSCORE_API_BASE = "https://api.walkscore.com/score"
WALKSCORE_CACHE_TTL = 2592000       # 30 days


def fetch_walk_score(
    address: str,
    api_key: str,
) -> dict | None:
    """Fetch walkability scores for an address from the Walk Score API.

    Args:
        address: Property street address.
        api_key: Walk Score API key (free at https://walkscore.com/professional/api).

    Returns:
        dict with keys walk_score (int), transit_score (int|None), bike_score (int|None),
        or None on any error.
    """
    if not api_key:
        logger.warning("Walk Score API key not provided")
        return None

    cache_key = f"walkscore_{hashlib.md5(address.encode()).hexdigest()}"

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url = f"{WALKSCORE_API_BASE}?address={quote(address)}&wsapikey={api_key}&format=json"

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, json.JSONDecodeError, TypeError) as exc:
        logger.warning("Walk Score API error for address=%s: %s", address, exc)
        return None

    if "walkscore" not in data:
        return None

    result: dict[str, Any] = {
        "walk_score": int(data["walkscore"]),
        "transit_score": None,
        "bike_score": None,
    }

    transit = data.get("transit")
    if isinstance(transit, dict) and "score" in transit:
        result["transit_score"] = int(transit["score"])

    bike = data.get("bike")
    if isinstance(bike, dict) and "score" in bike:
        result["bike_score"] = int(bike["score"])

    cache.set(cache_key, result, timeout=WALKSCORE_CACHE_TTL)
    return result
