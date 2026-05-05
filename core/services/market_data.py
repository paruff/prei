"""Market data service for neighborhood insights.

Provides ``refresh_market_snapshot`` which orchestrates all four market
adapters and persists their results to ``MarketSnapshot``.

Phase 2.2 — Neighborhood Insights.
"""

import logging
from decimal import Decimal

from core.integrations.market.comps import get_comps_for_listing
from core.integrations.market.crime import get_crime_score
from core.integrations.market.rents import get_rent_estimate_for_listing
from core.integrations.market.schools import get_school_rating
from core.models import Listing, MarketSnapshot

logger = logging.getLogger(__name__)


def refresh_market_snapshot(zip_code: str) -> MarketSnapshot:
    """Call all four market adapters and upsert a ``MarketSnapshot`` for *zip_code*.

    Each adapter call is wrapped in a ``try/except`` block.  If an adapter
    raises, the error is logged and the corresponding field defaults to
    ``Decimal("0")`` so that the snapshot is always saved.

    Args:
        zip_code: The five-digit (or formatted) ZIP code to refresh.

    Returns:
        The saved :class:`~core.models.MarketSnapshot` instance.
    """
    crime_score: Decimal = Decimal("0")
    school_rating: Decimal = Decimal("0")
    rent_index: Decimal = Decimal("0")
    price_trend: Decimal = Decimal("0")

    # --- crime score ---
    try:
        crime_score = get_crime_score(zip_code=zip_code)
    except Exception:
        logger.error(
            "market_data: get_crime_score failed for zip_code=%s",
            zip_code,
            exc_info=True,
        )

    # --- school rating ---
    try:
        school_rating = get_school_rating(zip_code=zip_code)
    except Exception:
        logger.error(
            "market_data: get_school_rating failed for zip_code=%s",
            zip_code,
            exc_info=True,
        )

    # --- rent index and price trend (require a representative listing) ---
    listing = Listing.objects.filter(zip_code=zip_code).first()
    if listing is not None:
        try:
            rent_index = get_rent_estimate_for_listing(listing)
        except Exception:
            logger.error(
                "market_data: get_rent_estimate_for_listing failed for zip_code=%s",
                zip_code,
                exc_info=True,
            )

        try:
            comps = get_comps_for_listing(listing)
            if comps:
                avg_comp_price = sum(c["price"] for c in comps) / Decimal(len(comps))
                listing_price: Decimal = listing.price
                if listing_price != Decimal("0"):
                    price_trend = (
                        (avg_comp_price - listing_price) / listing_price
                    ).quantize(Decimal("0.0001"))
        except Exception:
            logger.error(
                "market_data: get_comps_for_listing failed for zip_code=%s",
                zip_code,
                exc_info=True,
            )

    snapshot, _ = MarketSnapshot.objects.update_or_create(
        zip_code=zip_code,
        defaults={
            "area_type": "zip",
            "rent_index": rent_index,
            "price_trend": price_trend,
            "crime_score": crime_score,
            "school_rating": school_rating,
        },
    )
    return snapshot
