"""Market scoring primitives: 1% rule, GRM, price-to-rent, normalization helpers.

The underwriting score itself lives in ``core.services.scoring`` (Django-coupled).
This module holds the pure market/listing primitives shared across services.
"""

from __future__ import annotations

from decimal import Decimal
import logging

from investor_app.finance.utils import to_decimal

logger = logging.getLogger(__name__)


def one_percent_rule(monthly_rent: Decimal, purchase_price: Decimal) -> bool:
    """Evaluate the 1% Rule for a rental property.

    The 1% Rule is a quick pass/fail filter: monthly rent should be at least
    1% of the purchase price to indicate a potentially viable rental investment.

    Args:
        monthly_rent: Expected gross monthly rental income.
        purchase_price: Total purchase price of the property.

    Returns:
        True if monthly_rent / purchase_price >= 0.01, False otherwise.

    Raises:
        ValueError: If purchase_price is zero or negative.
    """
    pp = to_decimal(purchase_price)
    if pp <= Decimal("0"):
        raise ValueError(
            f"purchase_price must be greater than zero (received {purchase_price})"
        )
    return to_decimal(monthly_rent) / pp >= Decimal("0.01")


def gross_rent_multiplier(purchase_price: Decimal, annual_rent: Decimal) -> Decimal:
    """Calculate Gross Rent Multiplier (GRM).

    GRM = Purchase Price / Annual Rent

    Lower GRM values indicate better value relative to rental income.

    Args:
        purchase_price: Total purchase price of the property.
        annual_rent: Expected gross annual rental income.

    Returns:
        GRM as a Decimal.

    Raises:
        ValueError: If annual_rent is zero or negative.
    """
    ar = to_decimal(annual_rent)
    if ar <= Decimal("0"):
        raise ValueError(
            f"annual_rent must be greater than zero (received {annual_rent})"
        )
    return to_decimal(purchase_price) / ar


def price_to_rent_ratio(
    median_home_price: Decimal, annual_median_rent: Decimal
) -> Decimal:
    """Calculate market price-to-rent ratio.

    Args:
        median_home_price: Median home purchase price.
        annual_median_rent: Median annual rent.

    Returns:
        Price-to-rent ratio as a Decimal.

    Raises:
        ValueError: If annual_median_rent is zero or negative.
    """
    annual_rent = to_decimal(annual_median_rent)
    if annual_rent <= Decimal("0"):
        raise ValueError(
            "annual_median_rent must be greater than zero "
            f"(received {annual_median_rent})"
        )
    return to_decimal(median_home_price) / annual_rent


_EXCELLENT_PRICE_TO_RENT_THRESHOLD = Decimal("15")
_NEUTRAL_PRICE_TO_RENT_THRESHOLD = Decimal("20")
_MAX_PRICE_TO_RENT_THRESHOLD = Decimal("30")
_HIGH_SCORE_FLOOR = Decimal("60")
_HIGH_SCORE_RANGE = Decimal("40")
_LOW_SCORE_RANGE = Decimal("60")

_MIN_GROWTH_RATE_PERCENT = Decimal("-5")
_MAX_GROWTH_RATE_PERCENT = Decimal("10")
_GROWTH_RATE_RANGE = _MAX_GROWTH_RATE_PERCENT - _MIN_GROWTH_RATE_PERCENT


def normalize_market_price_to_rent_score(price_to_rent: Decimal) -> Decimal:
    """Convert price-to-rent ratio into a 0-100 market sub-score.

    Args:
        price_to_rent: Price-to-rent ratio for a market.

    Returns:
        Market sub-score in [0, 100], where higher is better.
    """
    if price_to_rent <= Decimal("0"):
        return Decimal("0")
    if price_to_rent < _EXCELLENT_PRICE_TO_RENT_THRESHOLD:
        return Decimal("100")
    if price_to_rent <= _NEUTRAL_PRICE_TO_RENT_THRESHOLD:
        return (_NEUTRAL_PRICE_TO_RENT_THRESHOLD - price_to_rent) / (
            _NEUTRAL_PRICE_TO_RENT_THRESHOLD - _EXCELLENT_PRICE_TO_RENT_THRESHOLD
        ) * _HIGH_SCORE_RANGE + _HIGH_SCORE_FLOOR
    if price_to_rent <= _MAX_PRICE_TO_RENT_THRESHOLD:
        return (
            (_MAX_PRICE_TO_RENT_THRESHOLD - price_to_rent)
            / (_MAX_PRICE_TO_RENT_THRESHOLD - _NEUTRAL_PRICE_TO_RENT_THRESHOLD)
            * _LOW_SCORE_RANGE
        )
    return Decimal("0")


def normalize_market_growth_rate_score(growth_rate: Decimal) -> Decimal:
    """Convert annual growth rate percent into a 0-100 market sub-score.

    Args:
        growth_rate: Annual growth rate as a percent value.

    Returns:
        Market sub-score in [0, 100], where higher is better.
    """
    clamped = max(_MIN_GROWTH_RATE_PERCENT, min(_MAX_GROWTH_RATE_PERCENT, growth_rate))
    return (clamped - _MIN_GROWTH_RATE_PERCENT) / _GROWTH_RATE_RANGE * Decimal("100")


def clamp_market_score(value: Decimal) -> Decimal:
    """Clamp a market score to the valid 0-100 range.

    Args:
        value: Raw market score value.

    Returns:
        Score clamped to [0, 100].
    """
    return max(Decimal("0"), min(Decimal("100"), value))
