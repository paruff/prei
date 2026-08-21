"""Rentometer API adapter for real rent estimates by ZIP code.

Fetches median rent estimates by address or ZIP+beds from Rentometer's API.
Fallback chain: Rentometer -> HUD FMR -> user-entered rent.

API docs: https://www.rentometer.com/api
Rate limit: 1,000 calls/month on basic plan — cache aggressively (7 days).
"""

from __future__ import annotations

import hashlib
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, cast

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

RENTO_METER_API_BASE = "https://www.rentometer.com/api/v1"
REQUEST_TIMEOUT = 15
CACHE_TTL_DAYS = 7


class RentometerError(Exception):
    """Base exception for Rentometer API errors."""


class RentometerClient:
    """Client for the Rentometer API."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or getattr(settings, "RENTO_METER_API_KEY", "")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        """Make a GET request to the Rentometer API."""
        url = f"{RENTO_METER_API_BASE}/{path.lstrip('/')}"
        try:
            resp = requests.get(
                url, headers=self._headers(), params=params, timeout=REQUEST_TIMEOUT
            )
            if resp.status_code == 401:
                raise RentometerError("Rentometer API key is missing or invalid")
            if resp.status_code == 404:
                raise RentometerError(f"No data found: {path}")
            resp.raise_for_status()
            data = resp.json()
        except RentometerError:
            raise
        except requests.RequestException as exc:
            # Timeouts, connection errors, and other non-2xx status codes
            # (e.g. 429 rate-limit, 5xx) all funnel through RentometerError
            # so every caller's single `except RentometerError` catches and
            # logs them, instead of a raw requests exception escaping
            # uncaught.
            raise RentometerError(f"Rentometer request failed: {exc}") from exc
        except ValueError as exc:
            # resp.json() raises a ValueError subclass on malformed JSON.
            raise RentometerError(f"Rentometer returned invalid JSON: {exc}") from exc
        return cast(dict[str, Any], data)

    def get_rent_by_address(
        self,
        address: str,
        city: str,
        state: str,
        zip_code: str,
    ) -> dict[str, Any] | None:
        """Get rent estimate for a specific address.

        Returns dict with median_rent, min_rent, max_rent, or None.
        """
        params = {
            "address": address,
            "city": city,
            "state": state,
            "zip": zip_code,
        }
        try:
            data = self._get("rent", params=params)
        except RentometerError:
            return None

        result = data.get("data", data)
        if not result or not result.get("median"):
            return None

        return {
            "median_rent": _parse_rent(result.get("median")),
            "min_rent": _parse_rent(result.get("min")),
            "max_rent": _parse_rent(result.get("max")),
            "count": result.get("count", 0),
            "city": result.get("city", ""),
            "state": result.get("state", ""),
        }


def _parse_rent(value: Any) -> Decimal | None:
    """Parse a rent value to Decimal."""
    if value is None or value == "":
        return None
    try:
        dec = Decimal(str(value)).quantize(Decimal("0.01"))
    except InvalidOperation, ValueError, TypeError:
        return None
    if dec <= 0:
        return None
    return dec


# ── Cache (Django's cache framework — same pattern as walkscore.py) ──────

_CACHE_TTL_SECONDS = CACHE_TTL_DAYS * 86400


def _cache_key(
    address: str | None,
    city: str | None,
    state: str | None,
    zip_code: str | None,
    bedrooms: int,
) -> str:
    raw = f"{address or ''}|{city or ''}|{state or ''}|{zip_code or ''}|{bedrooms}"
    return f"rentometer_{hashlib.sha256(raw.encode()).hexdigest()}"


def get_rent_estimate(
    zip_code: str | None = None,
    address: str | None = None,
    city: str | None = None,
    state: str | None = None,
    bedrooms: int = 2,
) -> Decimal | None:
    """Get a rent estimate for a location from Rentometer.

    Falls back to returning None if no API key or no data found.

    Args:
        zip_code: 5-digit ZIP code.
        address: Street address (improves accuracy).
        city: City name.
        state: 2-letter state code.
        bedrooms: Number of bedrooms. Used today only to differentiate cache
            entries (not yet passed to the Rentometer API call itself).

    Returns:
        Monthly median rent as Decimal, or None if unavailable.
    """
    client = RentometerClient()
    if not client.api_key:
        logger.debug("RENTO_METER_API_KEY not configured — skipping Rentometer")
        return None

    cache_key = _cache_key(address, city, state, zip_code, bedrooms)

    cached = cache.get(cache_key)
    if cached is not None:
        median = cached.get("median_rent") if cached else None
        return cast(Decimal, median) if median else None

    # Make API call
    if not address or not city or not state or not zip_code:
        logger.debug("Incomplete address for Rentometer lookup")
        cache.set(cache_key, {}, timeout=_CACHE_TTL_SECONDS)
        return None

    try:
        result = client.get_rent_by_address(address, city, state, zip_code)
        cache.set(cache_key, result or {}, timeout=_CACHE_TTL_SECONDS)
        if result and result.get("median_rent"):
            logger.debug(
                "Rentometer: %s %s, %s %s = $%s",
                address,
                city,
                state,
                zip_code,
                result["median_rent"],
            )
            return cast(Decimal, result["median_rent"])
    except RentometerError as exc:
        logger.warning("Rentometer lookup failed for %s: %s", zip_code, exc)
        cache.set(cache_key, {}, timeout=_CACHE_TTL_SECONDS)

    return None
