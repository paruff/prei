"""ATTOM pre-foreclosure notice integration.

Wires the existing :class:`ATTOMAdapter` to fetch pre-foreclosure
notices (NOD, NTS, Lis Pendens) for target ZIP codes and normalizes
the response into the :class:`CountyForeclosureNotice` schema.

Human Gate DISC-HG-4
---------------------
Before using this module in production, confirm that your ATTOM
subscription covers the ``/preforeclosure/detail`` endpoint, not just
the property detail/comps endpoints.  If your plan does *not* include
preforeclosure data, the API will return a ``404 No rule matched``
response and this module will return empty results.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from django.utils import timezone

from core.integrations.sources.attom_adapter import (
    ATTOMAdapter,
    ATTOMAPIError,
    ATTOMAuthenticationError,
    ATTOMRateLimitError,
)
from core.models import CountyForeclosureNotice

logger = logging.getLogger("prei.attom.preforeclosure")

# Default search radius in miles
DEFAULT_RADIUS = 25

# ═══════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════


def fetch_attom_preforeclosure(
    zip_code: str,
    radius: int = DEFAULT_RADIUS,
) -> list[dict[str, Any]]:
    """Fetch pre-foreclosure notices for a ZIP code from ATTOM.

    Returns a list of dicts, each ready for upsert into
    :class:`CountyForeclosureNotice`.  Returns an empty list with a
    logged warning when:

    * The API key is missing or invalid
    * The subscription does not cover the preforeclosure endpoint
    * No active preforeclosure notices are found for the given ZIP

    Args:
        zip_code: 5-digit US ZIP code to search.
        radius: Search radius in miles (default 25).

    Returns:
        List of CountyForeclosureNotice-ready dicts.
    """
    logger.info(
        "ATTOM preforeclosure: fetching for ZIP=%s (radius=%d)", zip_code, radius
    )

    adapter = ATTOMAdapter()

    try:
        raw = adapter.fetch_foreclosure_data(postalcode=zip_code, radius=radius)
    except ATTOMAuthenticationError:
        logger.warning("ATTOM: API key missing or invalid")
        return []
    except ATTOMRateLimitError:
        logger.warning("ATTOM: rate limit exceeded for ZIP=%s", zip_code)
        return []
    except ATTOMAPIError as exc:
        logger.warning("ATTOM: API error for ZIP=%s: %s", zip_code, exc)
        return []

    # Normalize each property in the response
    properties = _extract_properties(raw)
    if not properties:
        logger.info("ATTOM preforeclosure: no properties found for ZIP=%s", zip_code)
        return []

    notices: list[dict[str, Any]] = []
    errors = 0

    for prop in properties:
        try:
            notice = _normalize_to_county_notice(prop)
            if notice is not None:
                notices.append(notice)
        except Exception as exc:
            errors += 1
            logger.debug("ATTOM: failed to normalize property: %s", exc)
            continue

    if errors:
        logger.warning("ATTOM: %d property/ies failed to normalize", errors)

    logger.info(
        "ATTOM preforeclosure: %d notice(s) for ZIP=%s",
        len(notices),
        zip_code,
    )
    return notices


# ═══════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════


def _extract_properties(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract the list of property dicts from an ATTOM API response.

    The ATTOM ``/preforeclosure/detail`` endpoint may return results
    under ``property`` (list or single dict) or ``properties``.
    """
    # Response might have "property" as a list or a single dict
    prop = raw.get("property") or raw.get("properties") or []
    if isinstance(prop, dict):
        return [prop]
    if isinstance(prop, list):
        return prop
    return []


def _normalize_to_county_notice(
    attom_data: dict[str, Any],
) -> dict[str, Any] | None:
    """Normalize one ATTOM property response to a CountyForeclosureNotice dict.

    Args:
        attom_data: A single property dict from the ATTOM API.

    Returns:
        A dict matching the CountyForeclosureNotice model, or ``None``
        if the data is missing a required field (case_number).
    """
    address = attom_data.get("address", {}) or {}
    preforeclosure = attom_data.get("preforeclosure", {}) or {}

    case_number = str(preforeclosure.get("caseNumber", "") or "").strip()
    if not case_number:
        return None  # without a case number we cannot upsert

    now = timezone.now()

    notice: dict[str, Any] = {
        # ── Identity ──────────────────────────────────────────────
        "case_number": case_number,
        "document_type": _attom_stage_to_document_type(
            str(preforeclosure.get("stage", "") or "")
        ),
        # ── Borrower / lender ────────────────────────────────────
        "borrower_name": "",
        "lender_name": str(preforeclosure.get("lenderName", "") or ""),
        "trustee_name": "",
        # ── Location ─────────────────────────────────────────────
        "address": str(address.get("line1", "") or "").strip(),
        "city": str(address.get("locality", "") or "").strip(),
        "state": str(address.get("countrySubd", "") or "").strip(),
        "zip_code": str(address.get("postal1", "") or "").strip(),
        "county": str(address.get("county", "") or "").strip(),
        # ── Dates ────────────────────────────────────────────────
        "filing_date": _parse_attom_date(preforeclosure.get("date")),
        "sale_date": _parse_attom_date(preforeclosure.get("auctionDate")),
        "auction_time": "",
        "auction_location": "",
        # ── Financials ───────────────────────────────────────────
        "opening_bid": None,
        "unpaid_balance": _safe_decimal(preforeclosure.get("amount")),
        "estimated_value": _safe_decimal(
            attom_data.get("avm", {}).get("amount", {}).get("value")
        ),
        # ── Identifiers ──────────────────────────────────────────
        "parcel_number": str(
            attom_data.get("summary", {}).get("attainableparcel", "") or ""
        ).strip(),
        "source_url": "",
        # ── Audit trail ──────────────────────────────────────────
        "raw_data": {
            "attom_case_number": case_number,
            "attom_stage": preforeclosure.get("stage"),
            "latitude": address.get("latitude"),
            "longitude": address.get("longitude"),
            "property_type": attom_data.get("summary", {}).get("proptype"),
        },
        "scraped_at": now,
        "last_seen_at": now,
    }

    return notice


def _attom_stage_to_document_type(stage: str) -> str:
    """Map ATTOM foreclosure stage to CountyForeclosureNotice.DocumentType.

    The ATTOM API returns stage labels that vary by jurisdiction.
    This mapping handles the most common values.
    """
    stage_lower = stage.lower().strip()

    # Notice of Default / Preforeclosure
    if any(
        kw in stage_lower for kw in ["pre-foreclosure", "preforeclosure", "default"]
    ):
        return CountyForeclosureNotice.DocumentType.NOD

    # Lis Pendens
    if "lis pendens" in stage_lower:
        return CountyForeclosureNotice.DocumentType.LIS_PENDENS

    # Notice of Trustee Sale / Auction
    if any(
        kw in stage_lower
        for kw in ["notice of sale", "trustee sale", "trustee's sale", "auction"]
    ):
        return CountyForeclosureNotice.DocumentType.NTS

    # Sheriff sale
    if "sheriff" in stage_lower:
        return CountyForeclosureNotice.DocumentType.SHERIFF_SALE

    # Default to NOD for preforeclosure data
    return CountyForeclosureNotice.DocumentType.NOD


def _parse_attom_date(date_val: Any) -> str | None:
    """Parse an ATTOM date value to ISO date string.

    ATTOM returns dates in "YYYY-MM-DD" format or occasionally
    "YYYY-MM-DD HH:MM:SS".
    """
    if not date_val:
        return None

    date_str = str(date_val).strip()

    # Already ISO date
    if len(date_str) >= 10:
        try:
            from datetime import datetime as dt

            return dt.strptime(date_str[:10], "%Y-%m-%d").date().isoformat()
        except ValueError:
            pass

    # Try other common formats
    for fmt in ("%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y"):
        try:
            from datetime import datetime as dt

            return dt.strptime(date_str, fmt).date().isoformat()
        except ValueError:
            continue

    return date_str[:10] if len(date_str) >= 10 else date_str


def _safe_decimal(value: Any) -> Decimal | None:
    """Safely convert a value to Decimal."""
    if value is None or value == "" or value == 0:
        return None
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return None
