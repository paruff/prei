import json
import logging
from decimal import Decimal

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

GREATSCHOOLS_API_BASE = "https://api.greatschools.org/schools/nearby"
GREATSCHOOLS_CACHE_TTL = 2592000  # 30 days


def get_school_rating(
    zip_code: str | None = None, city: str | None = None, state: str | None = None
) -> Decimal:
    """Return a dummy school rating (0-10)."""
    if state == "TX":
        return Decimal("8.0")
    if state == "CA":
        return Decimal("7.0")
    return Decimal("6.5")


def fetch_school_rating(
    zip_code: str,
    api_key: str,
) -> Decimal | None:
    """Fetch average school rating for a ZIP code from the GreatSchools API.

    Args:
        zip_code: 5-digit ZIP code.
        api_key: GreatSchools API key (free at https://greatschools.org/api).

    Returns:
        Decimal average school rating (0-10 scale), or None on error.
    """
    if not api_key:
        logger.warning("GreatSchools API key not provided")
        return None

    cache_key = f"greatschools_rating_{zip_code}"

    cached = cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[no-any-return]

    url = f"{GREATSCHOOLS_API_BASE}?zip={zip_code}&key={api_key}"

    try:
        resp = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
        resp.raise_for_status()
        schools = resp.json()
    except requests.RequestException, json.JSONDecodeError, TypeError:
        logger.warning("GreatSchools API error for zip=%s", zip_code)
        return None

    if not isinstance(schools, list) or len(schools) == 0:
        return None

    ratings = []
    for school in schools:
        rating = school.get("gsRating")
        if rating is not None:
            try:
                ratings.append(float(rating))
            except ValueError, TypeError:
                continue

    if not ratings:
        return None

    avg = sum(ratings) / len(ratings)
    result = Decimal(str(avg)).quantize(Decimal("0.1"))

    cache.set(cache_key, result, timeout=GREATSCHOOLS_CACHE_TTL)
    return result
