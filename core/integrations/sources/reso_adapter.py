"""RESO Web API adapter for MLS data feed integration.

Implements the RESO Web API standard for MLS data feed integration,
supporting OData v4 queries, authentication, pagination, and data normalization.

RESO Web API Specification: https://www.reso.org/web-api/
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Iterator
from urllib.parse import urlencode, urljoin

import requests
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class RESOAPIError(Exception):
    """Base exception for RESO Web API errors."""

    pass


class RESOAuthenticationError(RESOAPIError):
    """Authentication failed with RESO Web API."""

    pass


class RESORateLimitError(RESOAPIError):
    """Rate limit exceeded for RESO Web API."""

    pass


class RESOAPIError(RESOAPIError):
    """General RESO Web API error."""

    pass


class RESOAdapter:
    """
    Adapter for RESO Web API (MLS data feed).

    Implements OData v4 queries for MLS data feed integration,
    supporting Property, Member, Office, and Media resources.

    RESO Web API Specification: https://www.reso.org/web-api/
    """

    # Standard RESO Web API endpoints
    DEFAULT_BASE_URL = "https://api.mls.example.com/odata"

    # Standard RESO resource types
    RESOURCE_TYPES = [
        "Property",
        "Member",
        "Office",
        "Media",
        "OpenHouse",
        "Room",
        "Unit",
    ]

    # Standard OData query options
    ODATA_QUERY_OPTIONS = [
        "$filter",
        "$select",
        "$expand",
        "$orderby",
        "$top",
        "$skip",
        "$count",
        "$skip",
        "$top",
        "$inlinecount",
    ]

    # Cache duration for property details (12 hours)
    CACHE_DURATION = 43200  # 12 hours in seconds
    MAX_RETRIES = 3
    REQUEST_TIMEOUT = 30  # seconds

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        access_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        token_url: Optional[str] = None,
    ):
        """
        Initialize RESO Web API adapter.

        Args:
            base_url: RESO Web API base URL (OData service endpoint)
            username: Username for Basic Auth (optional)
            password: Password for Basic Auth (optional)
            access_token: Bearer token for OAuth2 (optional)
            client_id: OAuth2 client ID (optional)
            client_secret: OAuth2 client secret (optional)
            token_url: OAuth2 token endpoint URL (optional)
        """
        self.base_url = base_url or os.getenv("RESO_API_BASE_URL", self.DEFAULT_BASE_URL)
        self.username = username or os.getenv("RESO_USERNAME")
        self.password = password or os.getenv("RESO_PASSWORD")
        self.access_token = access_token or os.getenv("RESO_ACCESS_TOKEN")
        self.client_id = client_id or os.getenv("RESO_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("RESO_CLIENT_SECRET")
        self.token_url = token_url or os.getenv("RESO_TOKEN_URL")

        self.session = requests.Session()
        self._access_token: Optional[str] = self.access_token
        self._token_expiry: Optional[datetime] = None

        self._setup_auth()

    def _setup_auth(self) -> None:
        """Configure authentication headers for the session."""
        headers: Dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "PREI-RESO-Adapter/1.0",
        }

        if self.access_token:
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
        elif self.username and self.password:
            import base64
            credentials = base64.b64encode(
                f"{self.username}:{self.password}".encode()
            ).decode()
            self.session.headers.update({"Authorization": f"Basic {credentials}"})

        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _get_access_token(self) -> Optional[str]:
        """Obtain OAuth2 access token if client credentials are configured."""
        if not self.client_id or not self.client_secret or not self.token_url:
            return None

        if self._access_token and self._token_expiry:
            if timezone.now() < self._token_expiry - timedelta(minutes=5):
                return self._access_token

        try:
            response = requests.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=10,
            )
            response.raise_for_status()
            token_data = response.json()
            self._access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)
            self._token_expiry = timezone.now() + timedelta(seconds=expires_in - 60)
            return self._access_token
        except Exception as e:
            logger.error(f"Failed to obtain access token: {e}")
            raise RESOAuthenticationError(f"Failed to obtain access token: {e}")

    def _get_headers(self) -> Dict[str, str]:
        """Build request headers with current authentication."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "PREI-RESO-Adapter/1.0",
        }

        if self.access_token or self.client_id:
            token = self._get_access_token()
            if token:
                return {**self.session.headers, "Authorization": f"Bearer {token}"}

        return self.session.headers

    def _execute_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data

        Returns:
            Parsed JSON response

        Raises:
            RESOAuthenticationError: Authentication failed
            RESORateLimitError: Rate limit exceeded
            RESOAPIError: Other API errors
        """
        url = urljoin(self.base_url, endpoint)
        headers = self._get_headers()

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=data,
                    timeout=self.REQUEST_TIMEOUT,
                )

                if response.status_code == 401:
                    # Token may be expired, force refresh
                    if self.access_token or self.client_id:
                        self._access_token = None
                        self._token_expiry = None
                        if self._get_access_token():
                            continue
                    raise RESOAuthenticationError("Authentication failed")

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    if attempt < self.MAX_RETRIES - 1:
                        logger.warning(f"Rate limited, waiting {retry_after}s before retry")
                        time.sleep(retry_after)
                        continue
                    raise RESORateLimitError("Rate limit exceeded")

                if not response.ok:
                    raise RESOAPIError(
                        f"API error: {response.status_code} - {response.text}"
                    )

                return response.json()

            except requests.exceptions.Timeout:
                if attempt == self.MAX_RETRIES - 1:
                    raise RESOAPIError("Request timeout")
                time.sleep(2 ** attempt)  # Exponential backoff

            except requests.exceptions.RequestException as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise RESOAPIError(f"Request failed: {e}")
                time.sleep(2 ** attempt)

        raise RESOAPIError("Max retries exceeded")

    def _build_odata_query(
        self,
        filter_expr: Optional[str] = None,
        select: Optional[List[str]] = None,
        expand: Optional[List[str]] = None,
        order_by: Optional[str] = None,
        top: Optional[int] = None,
        skip: int = 0,
        count: bool = False,
    ) -> Dict[str, str]:
        """Build OData query parameters."""
        params = {}

        if filter_expr:
            params["$filter"] = filter_expr
        if select:
            params["$select"] = ",".join(select)
        if expand:
            params["$expand"] = ",".join(expand)
        if order_by:
            params["$orderby"] = order_by
        if top is not None:
            params["$top"] = top
        if skip:
            params["$skip"] = skip
        if count:
            params["$count"] = "true"

        return params

    def _build_filter(
        self,
        field: str,
        operator: str,
        value: Any,
    ) -> str:
        """Build OData filter expression."""
        if isinstance(value, str):
            value = f"'{value}'"
        elif isinstance(value, datetime):
            value = value.strftime("%Y-%m-%dT%H:%M:%SZ")
        elif isinstance(value, bool):
            value = str(value).lower()
        return f"{field} {operator} {value}"

    def build_filter(
        self,
        filters: List[Dict[str, Any]],
    ) -> str:
        """Build complex OData filter from filter conditions.

        Args:
            filters: List of filter dicts with keys: field, operator, value
                Operators: eq, ne, gt, ge, lt, le, contains, startswith, endswith

        Returns:
            OData filter string
        """
        filter_parts = []
        for f in filters:
            field = f["field"]
            operator = f["operator"]
            value = f["value"]
            filter_parts.append(self._build_filter(field, operator, value))
        return " and ".join(filter_parts)

    def _get_cache_key(self, resource: str, params: Dict[str, Any]) -> str:
        """Generate cache key for request."""
        key_data = f"{self.base_url}/{resource}?{urlencode(sorted(params.items()))}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _get_cached(self, resource: str, params: Dict[str, Any]) -> Optional[Dict]:
        """Get cached response if available."""
        cache_key = self._get_cache_key(resource, params)
        return cache.get(cache_key)

    def _set_cache(self, resource: str, params: Dict[str, Any], data: Dict) -> None:
        """Cache response data."""
        cache_key = self._get_cache_key(resource, params)
        cache.set(cache_key, data, timeout=self.CACHE_DURATION)

    # ─── Property Resource Methods ────────────────────────────────────────

    def fetch_property(
        self,
        listing_id: str,
        expand: Optional[List[str]] = None,
        select: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Fetch a single property by ListingId.

        Args:
            listing_id: MLS Listing ID (ListingKey)
            expand: Navigation properties to expand (Media, OpenHouse, etc.)
            select: Properties to return (OData $select)

        Returns:
            Property data dictionary
        """
        params = self._build_odata_query(
            expand=expand,
            select=select,
        )
        endpoint = f"Property('{listing_id}')"
        return self._execute_request("GET", endpoint, params=params)

    def query_properties(
        self,
        filter_expr: Optional[str] = None,
        select: Optional[List[str]] = None,
        expand: Optional[List[str]] = None,
        order_by: Optional[str] = None,
        top: int = 100,
        skip: int = 0,
        count: bool = False,
    ) -> Dict[str, Any]:
        """
        Query properties with OData filters.

        Args:
            filter_expr: OData $filter expression
            select: Properties to return ($select)
            expand: Navigation properties to expand ($expand)
            order_by: Sort order ($orderby)
            top: Maximum results ($top)
            skip: Records to skip ($skip)
            count: Include total count ($count)

        Returns:
            Dictionary with 'value' (list of properties) and optional '@odata.count'
        """
        params = self._build_odata_query(
            filter_expr=filter_expr,
            select=select,
            expand=expand,
            order_by=order_by,
            top=top,
            skip=skip,
            count=count,
        )
        return self._execute_request("GET", "Property", params=params)

    def search_properties(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        postal_code: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        min_beds: Optional[int] = None,
        max_beds: Optional[int] = None,
        min_baths: Optional[Decimal] = None,
        max_baths: Optional[Decimal] = None,
        property_type: Optional[str] = None,
        status: Optional[str] = None,
        min_sqft: Optional[int] = None,
        max_sqft: Optional[int] = None,
        listing_status: Optional[str] = "Active",
        days_on_market_max: Optional[int] = None,
        top: int = 100,
        skip: int = 0,
    ) -> Dict[str, Any]:
        """
        Search properties with common filters.

        Args:
            city: City name
            state: State abbreviation (e.g., "TX")
            postal_code: ZIP code
            min_price: Minimum list price
            max_price: Maximum list price
            min_beds: Minimum bedrooms
            max_beds: Maximum bedrooms
            min_baths: Minimum bathrooms
            max_baths: Maximum bathrooms
            property_type: Property type (SFH, Condo, etc.)
            status: Listing status (Active, Pending, Closed)
            min_sqft: Minimum square footage
            max_sqft: Maximum square footage
            listing_status: Listing status filter
            days_on_market_max: Maximum days on market
            top: Maximum results
            skip: Records to skip

        Returns:
            Dictionary with property listings
        """
        filters = []

        if city:
            filters.append({"field": "City", "operator": "eq", "value": city})
        if state:
            filters.append({"field": "StateOrProvince", "operator": "eq", "value": state})
        if postal_code:
            filters.append({"field": "PostalCode", "operator": "eq", "value": postal_code})
        if min_price is not None:
            filters.append({"field": "ListPrice", "operator": "ge", "value": min_price})
        if max_price is not None:
            filters.append({"field": "ListPrice", "operator": "le", "value": max_price})
        if min_beds is not None:
            filters.append({"field": "BedroomsTotal", "operator": "ge", "value": min_beds})
        if max_beds is not None:
            filters.append({"field": "BedroomsTotal", "operator": "le", "value": max_beds})
        if min_baths is not None:
            filters.append({"field": "BathroomsTotalInteger", "operator": "ge", "value": min_baths})
        if max_baths is not None:
            filters.append({"field": "BathroomsTotalInteger", "operator": "le", "value": max_baths})
        if property_type:
            filters.append({"field": "PropertyType", "operator": "eq", "value": property_type})
        if listing_status:
            filters.append({"field": "StandardStatus", "operator": "eq", "value": listing_status})
        if min_sqft is not None:
            filters.append({"field": "LivingArea", "operator": "ge", "value": min_sqft})
        if max_sqft is not None:
            filters.append({"field": "LivingArea", "operator": "le", "value": max_sqft})
        if days_on_market_max is not None:
            filters.append({"field": "DaysOnMarket", "operator": "le", "value": days_on_market_max})

        filter_expr = self.build_filter(filters) if filters else None

        return self.query_properties(
            filter_expr=filter_expr,
            top=top,
            skip=skip,
        )

    def get_property_media(
        self,
        listing_id: str,
        top: int = 50,
    ) -> Dict[str, Any]:
        """Fetch media (photos, videos) for a property."""
        return self.query_properties(
            filter_expr=f"Media/any(m: m/ListingKey eq '{listing_id}')",
            top=top,
        )

    # ─── Member/Office Methods ─────────────────────────────────────────

    def fetch_member(
        self,
        member_id: str,
        expand: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Fetch agent/broker details by MemberKey."""
        params = self._build_odata_query(expand=expand)
        endpoint = f"Member('{member_id}')"
        return self._execute_request("GET", endpoint, params=params)

    def query_members(
        self,
        filter_expr: Optional[str] = None,
        select: Optional[List[str]] = None,
        top: int = 100,
        skip: int = 0,
    ) -> Dict[str, Any]:
        """Query members (agents/brokers)."""
        params = self._build_odata_query(
            filter_expr=filter_expr,
            select=select,
            top=top,
            skip=skip,
        )
        return self._execute_request("GET", "Member", params=params)

    def fetch_office(
        self,
        office_id: str,
        expand: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Fetch office details by OfficeKey."""
        params = self._build_odata_query(expand=expand)
        endpoint = f"Office('{office_id}')"
        return self._execute_request("GET", endpoint, params=params)

    # ─── Media/Media ───────────────────────────────────────────────────

    def fetch_media(
        self,
        listing_id: str,
        top: int = 50,
    ) -> Dict[str, Any]:
        """Fetch media (photos, videos) for a listing."""
        return self.query_properties(
            filter_expr=f"Media/any(m: m/ListingKey eq '{listing_id}')",
            select=["MediaKey", "MediaURL", "MediaType", "Order", "MediaCategory", "Description"],
            top=top,
        )

    # ─── Pagination Helper ──────────────────────────────────────────────

    def iter_all(
        self,
        resource: str,
        filter_expr: Optional[str] = None,
        select: Optional[List[str]] = None,
        batch_size: int = 100,
    ) -> Iterator[Dict[str, Any]]:
        """
        Iterate through all pages of a resource.

        Args:
            resource: Resource name (Property, Member, etc.)
            filter_expr: OData filter expression
            select: Properties to select
            batch_size: Page size

        Yields:
            Individual resource records
        """
        skip = 0
        while True:
            result = self._execute_request(
                "GET",
                resource,
                params=self._build_odata_query(
                    filter_expr=filter_expr,
                    top=batch_size,
                    skip=skip,
                    count=True,
                ),
            )

            items = result.get("value", [])
            if not items:
                break

            for item in items:
                yield item

            if len(items) < batch_size:
                break

            skip += batch_size

    # ─── Cache Management ──────────────────────────────────────────────

    def clear_cache(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries matching pattern."""
        if pattern:
            # Would need a more sophisticated cache backend for pattern deletion
            logger.warning("Pattern-based cache clearing not fully implemented")
            return 0
        cache.clear()
        return 1

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics (requires django-redis or similar)."""
        return {
            "cache_backend": str(cache.__class__),
            "cache_duration_seconds": self.CACHE_DURATION,
        }

    # ─── Raw Query Support ──────────────────────────────────────────────

    def raw_query(
        self,
        resource: str,
        odata_query: str,
    ) -> Dict[str, Any]:
        """
        Execute raw OData query string.

        Args:
            resource: Resource name (Property, Member, etc.)
            odata_query: Raw OData query string (e.g., "$filter=City eq 'Austin'&$top=10")

        Returns:
            Query results
        """
        params = {}
        for pair in odata_query.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                if k in params:
                    if not isinstance(params[k], list):
                        params[k] = [params[k]]
                    params[k].append(v)
                else:
                    params[k] = v

        return self._execute_request("GET", resource, params=params)


# ─── Utility Functions ─────────────────────────────────────────────────


def normalize_property_type(ptype: Optional[str]) -> Optional[str]:
    """Normalize property type to standard values."""
    if not ptype:
        return None
    ptype = ptype.upper().strip()
    mapping = {
        "SINGLE FAMILY": "SFR",
        "SINGLE FAMILY RESIDENCE": "SFR",
        "SINGLE FAMILY DETACHED": "SFR",
        "CONDO": "CONDO",
        "CONDOMINIUM": "CONDO",
        "TOWNHOUSE": "TOWNHOUSE",
        "TOWN HOUSE": "TOWNHOUSE",
        "DUPLEX": "DUPLEX",
        "TRIPLEX": "TRIPLEX",
        "FOURPLEX": "FOURPLEX",
        "MULTIFAMILY": "MULTIFAMILY",
        "APARTMENT": "APARTMENT",
        "COMMERCIAL": "COMMERCIAL",
        "LAND": "LAND",
        "LOT": "LAND",
    }
    return mapping.get(ptype, ptype)


def normalize_property_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize raw RESO property data to internal format.

    Args:
        raw: Raw property data from RESO API

    Returns:
        Normalized property data dict
    """
    return {
        "source": "reso",
        "listing_id": raw.get("ListingId") or raw.get("ListingKey"),
        "address": raw.get("UnparsedAddress") or raw.get("StreetNumber", "") + " " + raw.get("StreetName", ""),
        "city": raw.get("City"),
        "state": raw.get("StateOrProvince"),
        "zip_code": raw.get("PostalCode"),
        "price": Decimal(str(raw.get("ListPrice", 0))) if raw.get("ListPrice") else None,
        "beds": int(raw.get("BedroomsTotal", 0)) if raw.get("BedroomsTotal") else None,
        "baths": Decimal(str(raw.get("BathroomsTotalInteger", 0))) if raw.get("BathroomsTotalInteger") else None,
        "sq_ft": int(raw.get("LivingArea", 0)) if raw.get("LivingArea") else None,
        "lot_size_sqft": int(raw.get("LotSizeSquareFeet", 0)) if raw.get("LotSizeSquareFeet") else None,
        "property_type": normalize_property_type(raw.get("PropertyType")),
        "property_sub_type": raw.get("PropertySubType"),
        "year_built": int(raw.get("YearBuilt", 0)) if raw.get("YearBuilt") else None,
        "lot_size_acres": Decimal(str(raw.get("LotSizeAcres", 0))) if raw.get("LotSizeAcres") else None,
        "days_on_market": int(raw.get("DaysOnMarket", 0)) if raw.get("DaysOnMarket") else None,
        "listing_status": raw.get("StandardStatus"),
        "listing_date": raw.get("ListingContractDate"),
        "expiration_date": raw.get("ExpirationDate"),
        "mls_number": raw.get("MlsNumber") or raw.get("MlsId"),
        "mls_id": raw.get("MlsId"),
        "latitude": Decimal(str(raw.get("Latitude", 0))) if raw.get("Latitude") else None,
        "longitude": Decimal(str(raw.get("Longitude", 0))) if raw.get("Longitude") else None,
        "photos": [
            {
                "url": m.get("MediaURL"),
                "type": m.get("MediaType", "Photo"),
                "caption": m.get("Description"),
                "order": m.get("Order", 0),
            }
            for m in raw.get("Media", [])
            if m.get("MediaURL")
        ],
        "virtual_tour_url": raw.get("VirtualTourURL"),
        "listing_url": raw.get("PublicRemarks") or raw.get("ListingURL"),
        "remarks": raw.get("PublicRemarks"),
        "private_remarks": raw.get("PrivateRemarks"),
        "agent_id": raw.get("ListAgentKey") or raw.get("ListAgentMlsId"),
        "office_id": raw.get("ListOfficeKey") or raw.get("ListOfficeMlsId"),
        "raw_data": raw,
    }


# Export main classes and functions
__all__ = [
    "RESOAdapter",
    "RESOAPIError",
    "RESOAuthenticationError",
    "RESORateLimitError",
    "RESOAPIError",
    "normalize_property_type",
    "normalize_property_data",
]