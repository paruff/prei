"""ATTOM Data Solutions API adapter for foreclosure data."""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)


class ATTOMAPIError(Exception):
    """Base exception for ATTOM API errors."""

    pass


class ATTOMAuthenticationError(ATTOMAPIError):
    """Authentication failed with ATTOM API."""

    pass


class ATTOMRateLimitError(ATTOMAPIError):
    """Rate limit exceeded for ATTOM API."""

    pass


class ATTOMAdapter:
    """
    Adapter for ATTOM Data Solutions API.

    Handles authentication, request management, rate limiting,
    and response normalization for foreclosure data.
    """

    BASE_URL = "https://api.attomdata.com/propertyapi/v1.0.0"
    CACHE_DURATION = 86400  # 24 hours in seconds

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ATTOM API adapter.

        Args:
            api_key: ATTOM API key. If None, reads from environment.
        """
        self.api_key = api_key or os.getenv("ATTOM_API_KEY", "")
        if not self.api_key:
            logger.warning("ATTOM API key not configured")

        self.session = requests.Session()
        self.session.headers.update(
            {"apikey": self.api_key, "Accept": "application/json"}
        )

    def fetch_property_detail(
        self, address: str, address2: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch property details from ATTOM API.

        Args:
            address: Street address (e.g., "123 Main St")
            address2: City, state, ZIP (e.g., "Miami, FL 33139")

        Returns:
            Property detail data from ATTOM API

        Raises:
            ATTOMAuthenticationError: If authentication fails
            ATTOMRateLimitError: If rate limit is exceeded
            ATTOMAPIError: For other API errors
        """
        endpoint = f"{self.BASE_URL}/property/detail"
        params: Dict[str, str] = {"address": address}

        if address2:
            params["address2"] = address2

        try:
            response = self.session.get(endpoint, params=params, timeout=10)

            # Track API usage
            self._track_api_call(endpoint, response.status_code)

            if response.status_code == 401:
                logger.error("ATTOM API authentication failed")
                raise ATTOMAuthenticationError("Invalid or expired API credentials")

            if response.status_code == 429:
                logger.warning("ATTOM API rate limit exceeded")
                rate_limit_reset = response.headers.get("X-RateLimit-Reset")
                raise ATTOMRateLimitError(
                    f"Rate limit exceeded. Resets at: {rate_limit_reset}"
                )

            if response.status_code != 200:
                logger.error(
                    f"ATTOM API error: {response.status_code} - {response.text}"
                )
                raise ATTOMAPIError(
                    f"API request failed with status {response.status_code}"
                )

            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"ATTOM API request timeout for {address}")
            raise ATTOMAPIError("Request timeout")
        except requests.exceptions.RequestException as e:
            logger.error(f"ATTOM API request error: {str(e)}")
            raise ATTOMAPIError(f"Request failed: {str(e)}")

    def fetch_foreclosure_data(
        self, geoid: Optional[str] = None, radius: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fetch foreclosure data from ATTOM API.

        Args:
            geoid: Geographic identifier
            radius: Search radius in miles

        Returns:
            Foreclosure data from ATTOM API

        Raises:
            ATTOMAuthenticationError: If authentication fails
            ATTOMRateLimitError: If rate limit is exceeded
            ATTOMAPIError: For other API errors
        """
        endpoint = f"{self.BASE_URL}/preforeclosure/detail"
        params: Dict[str, Any] = {}

        if geoid:
            params["geoid"] = geoid
        if radius:
            params["radius"] = radius

        try:
            response = self.session.get(endpoint, params=params, timeout=10)

            # Track API usage
            self._track_api_call(endpoint, response.status_code)

            if response.status_code == 401:
                logger.error("ATTOM API authentication failed")
                raise ATTOMAuthenticationError("Invalid or expired API credentials")

            if response.status_code == 429:
                logger.warning("ATTOM API rate limit exceeded")
                rate_limit_reset = response.headers.get("X-RateLimit-Reset")
                raise ATTOMRateLimitError(
                    f"Rate limit exceeded. Resets at: {rate_limit_reset}"
                )

            if response.status_code != 200:
                logger.error(
                    f"ATTOM API error: {response.status_code} - {response.text}"
                )
                raise ATTOMAPIError(
                    f"API request failed with status {response.status_code}"
                )

            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"ATTOM API request timeout for geoid {geoid}")
            raise ATTOMAPIError("Request timeout")
        except requests.exceptions.RequestException as e:
            logger.error(f"ATTOM API request error: {str(e)}")
            raise ATTOMAPIError(f"Request failed: {str(e)}")

    def fetch_with_cache(
        self, address: str, address2: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch property data with caching to handle rate limits.

        Args:
            address: Street address
            address2: City, state, ZIP

        Returns:
            Property data (from cache or fresh API call)
        """
        cache_key = self._generate_cache_key(address, address2)
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.info(f"Returning cached data for {address}")
            cached_data["_from_cache"] = True
            return cached_data

        try:
            data = self.fetch_property_detail(address, address2)
            # Cache successful response
            cache.set(cache_key, data, self.CACHE_DURATION)
            data["_from_cache"] = False
            return data
        except ATTOMRateLimitError:
            # If rate limited and no cache available, raise error
            logger.error(f"Rate limit exceeded and no cached data for {address}")
            raise

    def normalize_property(self, attom_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize ATTOM API response to internal ForeclosureProperty schema.

        Args:
            attom_data: Raw ATTOM API response

        Returns:
            Normalized property data matching ForeclosureProperty model
        """
        property_data = attom_data.get("property", {})
        address_data = property_data.get("address", {})
        building_data = property_data.get("building", {})
        rooms_data = building_data.get("rooms", {})
        size_data = building_data.get("size", {})
        summary_data = property_data.get("summary", {})
        preforeclosure_data = attom_data.get("preforeclosure", {})

        # Generate unique property ID
        property_id = self._generate_property_id(attom_data)

        # Map foreclosure stage
        foreclosure_status = self._map_foreclosure_stage(preforeclosure_data)

        # Map property type
        property_type = self._map_property_type(summary_data.get("proptype", ""))

        normalized = {
            "property_id": property_id,
            "data_source": "ATTOM",
            "data_timestamp": datetime.now(),
            # Address information
            "street": address_data.get("line1", ""),
            "city": address_data.get("locality", ""),
            "state": address_data.get("countrySubd", ""),
            "zip_code": address_data.get("postal1", ""),
            "county": address_data.get("county", ""),
            "latitude": self._safe_decimal(address_data.get("latitude")),
            "longitude": self._safe_decimal(address_data.get("longitude")),
            # Foreclosure details
            "foreclosure_status": foreclosure_status,
            "foreclosure_stage": preforeclosure_data.get("stage", ""),
            "filing_date": self._parse_date(preforeclosure_data.get("date")),
            "auction_date": self._parse_date(preforeclosure_data.get("auctionDate")),
            "unpaid_balance": self._safe_decimal(preforeclosure_data.get("amount")),
            "lender_name": preforeclosure_data.get("lenderName", ""),
            "case_number": preforeclosure_data.get("caseNumber", ""),
            # Property details
            "property_type": property_type,
            "bedrooms": int(rooms_data.get("beds", 0) or 0),
            "bathrooms": self._safe_decimal(rooms_data.get("bathstotal", 0)),
            "square_footage": int(size_data.get("universalsize", 0) or 0),
            "year_built": int(summary_data.get("yearbuilt", 0) or 0) or None,
            # Valuation
            "estimated_value": self._safe_decimal(
                attom_data.get("avm", {}).get("amount", {}).get("value")
            ),
            "tax_assessed_value": self._safe_decimal(summary_data.get("assessedValue")),
        }

        return normalized

    def _map_foreclosure_stage(self, preforeclosure_data: Dict[str, Any]) -> str:
        """
        Map ATTOM foreclosure stage to internal status.

        Args:
            preforeclosure_data: Foreclosure data from ATTOM

        Returns:
            Foreclosure status (preforeclosure, auction, reo, government)
        """
        stage = preforeclosure_data.get("stage", "").lower()

        if "pre" in stage or "default" in stage or "lis pendens" in stage:
            return "preforeclosure"
        elif "auction" in stage or "trustee" in stage:
            return "auction"
        elif "reo" in stage or "bank" in stage or "owned" in stage:
            return "reo"
        elif "government" in stage or "hud" in stage:
            return "government"

        # Default to preforeclosure if unknown
        return "preforeclosure"

    def _map_property_type(self, prop_type: str) -> str:
        """
        Map ATTOM property type to internal property type.

        Args:
            prop_type: ATTOM property type string

        Returns:
            Internal property type (single-family, condo, multi-family, commercial)
        """
        prop_type_lower = prop_type.lower()

        if "single" in prop_type_lower or "sfr" in prop_type_lower:
            return "single-family"
        elif "condo" in prop_type_lower or "condominium" in prop_type_lower:
            return "condo"
        elif "multi" in prop_type_lower or "duplex" in prop_type_lower:
            return "multi-family"
        elif "commercial" in prop_type_lower:
            return "commercial"

        # Default to single-family if unknown
        return "single-family"

    def _generate_property_id(self, attom_data: Dict[str, Any]) -> str:
        """
        Generate unique property ID from ATTOM data.

        Args:
            attom_data: ATTOM API response

        Returns:
            Unique property ID
        """
        address_data = attom_data.get("property", {}).get("address", {})
        address_str = (
            f"{address_data.get('line1', '')}"
            f"{address_data.get('locality', '')}"
            f"{address_data.get('countrySubd', '')}"
            f"{address_data.get('postal1', '')}"
        )
        hash_value = hashlib.md5(address_str.encode()).hexdigest()[:12]
        return f"ATTOM-{hash_value}"

    def _generate_cache_key(self, address: str, address2: Optional[str] = None) -> str:
        """
        Generate cache key for property data.

        Args:
            address: Street address
            address2: City, state, ZIP

        Returns:
            Cache key string
        """
        key_parts = [address]
        if address2:
            key_parts.append(address2)
        key_str = "_".join(key_parts)
        return f"attom_property_{hashlib.md5(key_str.encode()).hexdigest()}"

    def _track_api_call(self, endpoint: str, status_code: int) -> None:
        """
        Track API call for cost monitoring.

        Args:
            endpoint: API endpoint called
            status_code: HTTP status code
        """
        # Get cost per call from settings
        cost_per_call = Decimal(os.getenv("ATTOM_COST_PER_CALL", "0.01"))

        # Update call counter in cache
        today = datetime.now().date().isoformat()
        call_count_key = f"attom_calls_{today}"
        cost_key = f"attom_cost_{today}"

        current_calls = cache.get(call_count_key, 0) or 0
        current_cost = cache.get(cost_key, Decimal("0")) or Decimal("0")

        cache.set(call_count_key, current_calls + 1, 86400 * 7)  # Keep for 7 days

        if status_code == 200:
            # Only count successful calls toward cost
            cache.set(cost_key, current_cost + cost_per_call, 86400 * 7)

        logger.info(
            f"ATTOM API call tracked: {endpoint} - Status: {status_code} - "
            f"Total calls today: {current_calls + 1} - Cost today: ${current_cost + (cost_per_call if status_code == 200 else 0)}"
        )

    def _safe_decimal(self, value: Any) -> Optional[Decimal]:
        """
        Safely convert value to Decimal.

        Args:
            value: Value to convert

        Returns:
            Decimal value or None
        """
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        Parse date string to ISO format.

        Args:
            date_str: Date string from API

        Returns:
            ISO formatted date string or None
        """
        if not date_str:
            return None

        try:
            # Try parsing common date formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"]:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.date().isoformat()
                except ValueError:
                    continue

            # If no format matches, return as-is
            return date_str
        except Exception:
            return None

    def get_usage_stats(self, days: int = 1) -> Dict[str, Any]:
        """
        Get API usage statistics for the specified number of days.

        Args:
            days: Number of days to retrieve stats for

        Returns:
            Dictionary with usage statistics
        """
        stats: Dict[str, Any] = {
            "days": [],
            "total_calls": 0,
            "total_cost": Decimal("0"),
        }

        today = datetime.now().date()

        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.isoformat()

            call_count_key = f"attom_calls_{date_str}"
            cost_key = f"attom_cost_{date_str}"

            calls = cache.get(call_count_key, 0)
            cost = cache.get(cost_key, Decimal("0"))

            stats["days"].append(
                {"date": date_str, "calls": calls, "cost": float(cost)}
            )
            stats["total_calls"] += calls
            stats["total_cost"] += cost

        stats["total_cost"] = float(stats["total_cost"])

        return stats


def fetch(location: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch foreclosure properties from ATTOM API.

    This is a convenience function that matches the interface of other adapters.
    Note: This is a placeholder for basic adapter interface compatibility.

    TODO: Implement batch fetching with proper geoid/radius parameters for production use.
    For production, this should:
    1. Accept location parameter and convert to geoid
    2. Call fetch_foreclosure_data with appropriate radius
    3. Normalize and return property data

    Args:
        location: Optional location filter (not used for ATTOM batch fetch)

    Returns:
        List of normalized property dictionaries
    """
    logger.info("ATTOM fetch called - requires geoid/radius parameters for production")
    return []
