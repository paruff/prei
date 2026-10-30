"""Market trends adapter for fetching and classifying market cycle indicators.

This module provides adapters for various market data sources and
classification logic for determining market health status.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class MarketIndicatorData:
    """Data class for market indicator values."""

    indicator_type: str
    value: Decimal
    date_recorded: date
    source: str = ""
    notes: str = ""


def classify_market_health(
    indicator_type: str,
    value: Decimal,
    metro_area: str = "",
    median_income: Optional[Decimal] = None,
) -> str:
    """Classify market health status for a given indicator.

    Args:
        indicator_type: Type of indicator (median_price, dom, months_supply, etc.)
        value: The indicator value
        metro_area: Metropolitan area name (optional, for future context)
        median_income: Median household income for price-to-income calculations

    Returns:
        str: 'healthy', 'caution', or 'overheated'
    """
    if indicator_type == "median_price":
        if median_income is None or median_income <= 0:
            return "caution"  # Can't determine without income
        ratio = value / median_income
        if ratio <= Decimal("4.0"):
            return "healthy"
        elif ratio <= Decimal("5.0"):
            return "caution"
        else:
            return "overheated"

    elif indicator_type == "dom":
        # Days on Market: lower = hotter market
        # < 10 days = overheated, 10-30 days = caution, > 30 days = healthy
        if value < Decimal("10"):
            return "overheated"
        elif value < Decimal("30"):
            return "caution"
        else:
            return "healthy"

    elif indicator_type == "months_supply":
        # Months of supply: lower = seller's market (overheated)
        if value < Decimal("3"):
            return "overheated"
        elif value <= Decimal("6"):
            return "healthy"
        else:
            return "caution"  # > 6 months = buyer's market (declining)

    elif indicator_type == "price_to_income":
        # Price-to-income ratio
        if value <= Decimal("4.0"):
            return "healthy"
        elif value <= Decimal("5.0"):
            return "caution"
        else:
            return "overheated"

    elif indicator_type == "rent_growth_yoy":
        # Year-over-year rent growth
        if value < Decimal("0"):
            return "caution"  # Declining
        elif value <= Decimal("0.05"):  # 0-5%
            return "healthy"
        elif value <= Decimal("0.08"):  # 5-8%
            return "caution"
        else:
            return "overheated"  # > 8%

    else:
        return "caution"


def fetch_market_indicators(metro_area: str) -> List[Dict[str, Any]]:
    """Fetch market indicators for a metro area.

    This is a placeholder implementation. In production, this would
    fetch from Zillow Research API, Census, BLS, FRED, etc.

    Args:
        metro_area: Metropolitan Statistical Area name

    Returns:
        List of indicator data dictionaries
    """
    # Placeholder implementation - returns mock data for testing
    # In production, this would call external APIs
    from datetime import date
    from decimal import Decimal

    today = date.today()
    return [
        {
            "indicator_type": "median_price",
            "value": Decimal("425000"),
            "date_recorded": today,
            "source": "zillow",
            "notes": "Zillow Home Value Index",
        },
        {
            "indicator_type": "dom",
            "value": Decimal("28"),
            "date_recorded": today,
            "source": "zillow",
            "notes": "Zillow Days on Market",
        },
        {
            "indicator_type": "months_supply",
            "value": Decimal("3.5"),
            "date_recorded": today,
            "source": "zillow",
            "notes": "Zillow Months of Supply",
        },
        {
            "indicator_type": "price_to_income",
            "value": Decimal("4.2"),
            "date_recorded": today,
            "source": "census",
            "notes": "Census ACS median price / median income",
        },
        {
            "indicator_type": "rent_growth_yoy",
            "value": Decimal("0.045"),
            "date_recorded": today,
            "source": "zillow",
            "notes": "Zillow Observed Rent Index YoY",
        },
    ]


def get_indicator_history(
    metro_area: str, indicator_type: str, limit: int = 12
) -> List[Decimal]:
    """Return up to ``limit`` most recent values for an indicator, oldest first."""
    from core.models.growth import MarketIndicator

    qs = MarketIndicator.objects.filter(
        metro_area=metro_area,
        indicator_type=indicator_type,
    ).order_by("-date_recorded")[:limit]
    return [ind.value for ind in reversed(list(qs))]


def build_sparkline_points(
    values: List[Decimal], width: int = 100, height: int = 30
) -> str:
    """Convert a value series into SVG polyline points for a sparkline.

    Points are normalized to the ``width`` x ``height`` viewBox. A flat line
    is drawn when all values are equal, and the midpoint when empty/constant.

    Args:
        values: Series of Decimal values, oldest first.
        width: ViewBox width (default 100).
        height: ViewBox height (default 30).

    Returns:
        Space-separated "x,y" point string suitable for <polyline points=>.
    """
    mid = height // 2
    if not values:
        return ""
    if len(values) == 1:
        return f"0,{mid} {width},{mid}"

    v = [float(x) for x in values]
    lo, hi = min(v), max(v)
    rng = hi - lo
    if rng == 0:
        step = width / (len(v) - 1)
        return " ".join(f"{int(round(i * step))},{mid}" for i in range(len(v)))

    step = width / (len(v) - 1)
    pts = []
    for i, val in enumerate(v):
        x = int(round(i * step))
        y = int(round(height - (val - lo) / rng * height))
        pts.append(f"{x},{y}")
    return " ".join(pts)


def get_latest_indicators(metro_area: str) -> Dict[str, Any]:
    """Get latest indicators for a metro area.

    Stored ``MarketIndicator`` records take precedence; the adapter
    (``fetch_market_indicators``) fills in any indicator type with no
    stored record yet.

    Args:
        metro_area: Metropolitan Statistical Area name

    Returns:
        Dictionary mapping indicator types to their latest values,
        health classification, history, and sparkline points.
    """
    from core.models.growth import MarketIndicator, MarketIndicatorType

    # Median income context improves median_price classification.
    median_income = None
    try:
        from core.models.growth import MarketSnapshot

        snapshot = MarketSnapshot.objects.filter(
            msa_name__icontains=metro_area.split(",")[0].strip()
        ).first()
        if snapshot and snapshot.median_household_income:
            median_income = snapshot.median_household_income
    except Exception:
        logger.warning(
            "get_latest_indicators: MarketSnapshot median-income lookup failed "
            "for %s; classifying without income context",
            metro_area,
            exc_info=True,
        )
        median_income = None

    result: Dict[str, Any] = {}
    fetched: Dict[str, Dict[str, Any]] = {
        ind["indicator_type"]: ind for ind in fetch_market_indicators(metro_area)
    }

    for itype in MarketIndicatorType.values:
        latest = (
            MarketIndicator.objects.filter(metro_area=metro_area, indicator_type=itype)
            .order_by("-date_recorded")
            .first()
        )
        if latest is not None:
            value = latest.value
            date_recorded = latest.date_recorded
            source = latest.source
            history = get_indicator_history(metro_area, itype)
        elif itype in fetched:
            value = fetched[itype]["value"]
            date_recorded = fetched[itype]["date_recorded"]
            source = fetched[itype].get("source", "")
            history = [value]
        else:
            continue

        result[itype] = {
            "value": value,
            "date_recorded": date_recorded,
            "source": source,
            "health": classify_market_health(
                itype,
                value,
                metro_area=metro_area,
                median_income=median_income,
            ),
            "history": history,
            "sparkline": build_sparkline_points(history),
        }
    return result


def update_market_indicators(metro_area: str = "") -> Dict[str, Any]:
    """Update market indicators for one or all metro areas.

    This function would be called by the management command to
    fetch and store the latest indicator values.

    Args:
        metro_area: Specific metro area to update, or empty for all

    Returns:
        Dict with stats about the update operation
    """
    from core.models.growth import MarketIndicator

    if metro_area:
        metro_areas = [metro_area]
    else:
        # Get unique metro areas from existing indicators
        metro_areas = list(
            MarketIndicator.objects.values_list("metro_area", flat=True).distinct()
        )

    created = 0
    updated = 0
    errors = 0

    for metro in metro_areas:
        try:
            indicators = fetch_market_indicators(metro)
            for ind_data in indicators:
                obj, was_created = MarketIndicator.objects.update_or_create(
                    metro_area=metro,
                    indicator_type=ind_data["indicator_type"],
                    date_recorded=ind_data["date_recorded"],
                    defaults={
                        "value": ind_data["value"],
                        "source": ind_data.get("source", ""),
                        "notes": ind_data.get("notes", ""),
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
        except Exception:
            errors += 1
            # Log error in production
            pass

    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "metro_areas": metro_areas,
    }


def get_market_health_summary(metro_area: str) -> Dict[str, Any]:
    """Get a summary of market health for a metro area.

    Args:
        metro_area: Metropolitan Statistical Area name

    Returns:
        Dictionary with overall health and per-indicator details
    """
    indicators = get_latest_indicators(metro_area)

    health_counts = {"healthy": 0, "caution": 0, "overheated": 0}
    for ind_type, data in indicators.items():
        health = data.get("health", "caution")
        health_counts[health] += 1

    # Determine overall health
    if health_counts["overheated"] > health_counts["healthy"]:
        overall = "overheated"
    elif health_counts["caution"] > health_counts["healthy"]:
        overall = "caution"
    else:
        overall = "healthy"

    return {
        "metro_area": metro_area,
        "overall_health": overall,
        "health_counts": health_counts,
        "indicators": indicators,
    }
