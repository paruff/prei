"""Canonical schema and structural ingestion sanitizer for the DISCOVERY stage.

Ported from prei.pipeline.handlers.discovery (pydantic removed).
Creates an unyielding data normalization layer that maps erratic, multi-source
external data structures (MLS listings, county foreclosure scraps, wholesale
raw JSON dumps) into a clean, unified internal Python schema.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any


def _coerce_float(v: Any) -> float | None:
    """Coerce messy numeric inputs to float or None.

    Handles string representations ("1998", ""), float types (3.0),
    and missing/null values uniformly.
    """
    if v is None or v == "":
        return None
    try:
        return float(v)
    except ValueError, TypeError:
        return 0.0


def _coerce_beds(v: Any) -> int:
    """Coerce beds to int. Handles 3.0, "3", None."""
    if v is None or v == "":
        return 0
    try:
        return int(float(v))
    except ValueError, TypeError:
        return 0


def _coerce_baths(v: Any) -> float:
    """Coerce baths to float. Handles "2", 2, 2.5, None."""
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except ValueError, TypeError:
        return 0.0


def _coerce_sqft(v: Any) -> float | None:
    """Coerce sqft to Optional[float]."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except ValueError, TypeError:
        return None


def _coerce_year(v: Any) -> int | None:
    """Coerce year_built to Optional[int]."""
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except ValueError, TypeError:
        return None


@dataclass
class CanonicalPropertyPayload:
    """Unified internal schema for property data entering the pipeline.

    All fields are strictly typed. Secondary fields that cannot be extracted
    from a given source default to None rather than a magic value.

    Monetary fields (price, estimated_rent) are float in this transient DTO
    (behavior preserved from the prei port); Decimal conversion happens at the
    persistence boundary (core.services.discovery_processor).
    """

    source_id: str
    source_name: str
    raw_address: str
    address_hash: str
    price: float | None = None
    estimated_rent: float | None = None
    beds: int = 0
    baths: float = 0.0
    sqft: float | None = None
    year_built: int | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)


class DiscoverySanitizer:
    """Structural ingestion sanitizer for raw external property data.

    Usage::
        sanitizer = DiscoverySanitizer()
        payload = sanitizer.transform_input(raw_dict, source="mls_feed")
    """

    @staticmethod
    def clean_address(address: str) -> str:
        """Deterministic address string normalizer.

        Strips special characters, punctuation, extra whitespace,
        and casing differences.

        Examples::
            >>> DiscoverySanitizer.clean_address("123 Main St., Apt #4B ")
            '123 main st apt 4b'
        """
        if not address:
            return ""
        clean = address.lower().strip()
        clean = re.sub(r"[^\w\s]", "", clean)
        return " ".join(clean.split())

    @classmethod
    def compute_address_hash(cls, normalized_address: str) -> str:
        """Compute a SHA-256 hex digest of the normalized address.

        Serves as the structural anchor for unique asset validation.
        """
        return hashlib.sha256(normalized_address.encode("utf-8")).hexdigest()

    @classmethod
    def transform_input(
        cls,
        raw: dict[str, Any],
        source: str,
    ) -> CanonicalPropertyPayload:
        """Transform a raw external data dict into a canonical payload.

        Handles multiple common key schemas (MLS, county records, wholesale)
        with flexible key fallback chains.

        Args:
            raw: Raw data dict from an external source.
            source: Human-readable source name (e.g., "mls_feed",
                    "county_scraper", "wholesale_json").

        Returns:
            CanonicalPropertyPayload with normalized fields.

        Raises:
            ValueError: If no valid address can be extracted.
        """
        raw_address = (
            raw.get("address")
            or raw.get("FullStreetAddress")
            or raw.get("full_address")
            or raw.get("AddressFull")
            or ""
        )
        cleaned_addr = cls.clean_address(raw_address)
        if not cleaned_addr:
            raise ValueError(
                "Input properties must contain a valid, non-empty address field."
            )

        addr_hash = cls.compute_address_hash(cleaned_addr)

        return CanonicalPropertyPayload(
            source_id=str(
                raw.get("id")
                or raw.get("ListingKey")
                or raw.get("parcel_id")
                or raw.get("apn")
                or ""
            ),
            source_name=source,
            raw_address=raw_address,
            address_hash=addr_hash,
            price=_coerce_float(
                raw.get("price") or raw.get("ListPrice") or raw.get("sale_price")
            ),
            estimated_rent=_coerce_float(
                raw.get("rent") or raw.get("RentEstimate") or raw.get("estimated_rent")
            ),
            beds=_coerce_beds(raw.get("beds") or raw.get("BedroomsTotal")),
            baths=_coerce_baths(
                raw.get("baths")
                or raw.get("BathroomsTotalInteger")
                or raw.get("BathroomsFull")
            ),
            sqft=_coerce_sqft(
                raw.get("sqft") or raw.get("LivingArea") or raw.get("SquareFootage")
            ),
            year_built=_coerce_year(
                raw.get("year_built") or raw.get("YearBuilt") or raw.get("yearBuilt")
            ),
            raw_metadata=raw,
        )
