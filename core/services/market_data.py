"""Market data service for neighborhood insights.

Provides ``refresh_market_snapshot`` which orchestrates all four market
adapters and persists their results to ``MarketSnapshot``.

Phase 2.2 — Neighborhood Insights.  Updated in A-tasks (A4 + A5) to try
live API adapters first with dummy fallback.
"""

from __future__ import annotations

import logging
import os
from decimal import Decimal

from core.integrations.market.comps import (
    fetch_comps_for_listing,
    get_comps_for_listing,
)
from core.integrations.market.crime import get_crime_score
from core.integrations.market.rents import (
    fetch_rent_estimate,
    get_rent_estimate_for_listing,
)
from core.integrations.market.schools import fetch_school_rating, get_school_rating
from core.models import Listing, MarketSnapshot

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _resolve_api_key(env_var: str) -> str:
    """Return the API key from the environment, or empty string if unset."""
    return os.getenv(env_var, "")


def _build_source_tag(*flags: str) -> str:
    """Join non-empty source flags into a single source tag."""
    return ",".join(f for f in flags if f) or "dummy"


# ---------------------------------------------------------------------------
# refresh_market_snapshot
# ---------------------------------------------------------------------------


def refresh_market_snapshot(zip_code: str) -> MarketSnapshot:
    """Call all four market adapters and upsert a ``MarketSnapshot`` for *zip_code*.

    Tries live API adapters first (when the corresponding env-var key is set),
    falling back to the existing dummy adapters on ``None``, key absence, or
    any error.  The fallback path is logged at WARNING level so operators can
    see when real data is not being used.

    The ``MarketSnapshot.data_source`` field records which adapters contributed
    real data so snapshots sourced entirely from dummies are distinguishable.

    Each adapter call is wrapped in a ``try/except`` block.  If an adapter
    raises, the error is logged and the corresponding field defaults to
    ``Decimal("0")`` so the snapshot is always saved.

    Args:
        zip_code: The five-digit (or formatted) ZIP code to refresh.

    Returns:
        The saved :class:`~core.models.MarketSnapshot` instance with
        ``data_source`` populated.
    """
    # --- adapter inputs --------------------------------------------------
    listing: Listing | None = Listing.objects.filter(zip_code=zip_code).first()

    rentcast_key = _resolve_api_key("RENTCAST_API_KEY")
    greatschools_key = _resolve_api_key("GREATSCHOOLS_API_KEY")
    # ATTOM key read by fetch_comps_for_listing from ATTOM_API_KEY env var.

    source_flags: list[str] = []

    # --- crime score (always dummy — see TASK-A1 SPIKE / DECISION-2) -----
    crime_score: Decimal = Decimal("0")
    try:
        crime_score = get_crime_score(zip_code=zip_code)
        logger.warning(
            "market_data: crime_score for zip=%s uses PLACEHOLDER dummy value "
            "(no live crime API available per DECISION-2 Option C)",
            zip_code,
        )
    except Exception:
        logger.error(
            "market_data: get_crime_score failed for zip_code=%s",
            zip_code,
            exc_info=True,
        )

    # --- school rating (live GreatSchools → dummy fallback) ---------------
    school_rating: Decimal = Decimal("0")
    try:
        if greatschools_key:
            result = fetch_school_rating(zip_code, greatschools_key)
            if result is not None:
                school_rating = result
                source_flags.append("greatschools")
            else:
                logger.warning(
                    "market_data: fetch_school_rating returned None for zip=%s "
                    "— falling back to dummy school rating",
                    zip_code,
                )
                school_rating = get_school_rating(zip_code=zip_code)
        else:
            logger.warning(
                "market_data: GREATSCHOOLS_API_KEY not set — using dummy school "
                "rating for zip=%s",
                zip_code,
            )
            school_rating = get_school_rating(zip_code=zip_code)
    except Exception:
        logger.error(
            "market_data: school_rating adapter failed for zip=%s",
            zip_code,
            exc_info=True,
        )

    # --- rent index and price trend (require a listing) -------------------
    rent_index: Decimal = Decimal("0")
    price_trend: Decimal = Decimal("0")

    if listing is not None:
        # rent index (live RentCast → dummy fallback)
        try:
            if rentcast_key:
                result = fetch_rent_estimate(
                    listing.address,
                    rentcast_key,
                    zip_code=listing.zip_code or zip_code,
                )
                if result is not None:
                    rent_index = result
                    source_flags.append("rentcast")
                else:
                    logger.warning(
                        "market_data: fetch_rent_estimate returned None for "
                        "address=%s — falling back to dummy PPSF heuristic",
                        listing.address,
                    )
                    rent_index = get_rent_estimate_for_listing(listing)
            else:
                logger.warning(
                    "market_data: RENTCAST_API_KEY not set — using dummy "
                    "PPSF heuristic for address=%s",
                    listing.address,
                )
                rent_index = get_rent_estimate_for_listing(listing)
        except Exception:
            logger.error(
                "market_data: rent adapter failed for zip=%s", zip_code, exc_info=True
            )

        # price trend (live ATTOM comps → dummy fallback)
        try:
            comps = fetch_comps_for_listing(listing)
            if not comps:
                logger.warning(
                    "market_data: fetch_comps_for_listing returned empty for "
                    "address=%s — falling back to dummy comps",
                    listing.address,
                )
                comps = get_comps_for_listing(listing)
            else:
                source_flags.append("attom")
        except Exception:
            logger.error(
                "market_data: fetch_comps_for_listing failed for zip=%s",
                zip_code,
                exc_info=True,
            )
            try:
                comps = get_comps_for_listing(listing)
            except Exception:
                logger.error(
                    "market_data: get_comps_for_listing fallback also failed for zip=%s",
                    zip_code,
                    exc_info=True,
                )
                comps = []

        if comps:
            try:
                avg_comp_price = sum(c["price"] for c in comps) / Decimal(len(comps))
                listing_price: Decimal = listing.price
                if listing_price != Decimal("0"):
                    price_trend = (
                        (avg_comp_price - listing_price) / listing_price
                    ).quantize(Decimal("0.0001"))
            except Exception:
                logger.error(
                    "market_data: price_trend calculation failed for zip=%s",
                    zip_code,
                    exc_info=True,
                )

    source_tag = _build_source_tag(*source_flags)

    snapshot, _ = MarketSnapshot.objects.update_or_create(
        zip_code=zip_code,
        defaults={
            "area_type": "zip",
            "rent_index": rent_index,
            "price_trend": price_trend,
            "crime_score": crime_score,
            "school_rating": school_rating,
            "data_source": source_tag,
        },
    )
    return snapshot
