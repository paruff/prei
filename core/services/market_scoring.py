"""Market-level investor viability scoring service.

This module computes an investor-focused market score on a 0-100 scale
using weighted signals (price-to-rent, growth, diversity, and policy
friendliness). Weights are configurable via ``settings.MARKET_SCORE_WEIGHTS``.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Mapping

from django.conf import settings

from core.models import MarketSnapshot
from investor_app.finance.utils import (
    clamp_market_score,
    normalize_market_growth_rate_score,
    normalize_market_price_to_rent_score,
)

_DEFAULT_MARKET_SCORE_WEIGHTS: dict[str, Decimal] = {
    "price_to_rent": Decimal("0.25"),
    "population_growth": Decimal("0.20"),
    "employment_diversity": Decimal("0.20"),
    "landlord_friendliness": Decimal("0.25"),
    "rent_growth": Decimal("0.10"),
}


def _get_market_score_weights() -> dict[str, Decimal]:
    """Return validated score weights from settings with safe defaults."""
    configured = getattr(settings, "MARKET_SCORE_WEIGHTS", None)
    if not isinstance(configured, Mapping):
        return _DEFAULT_MARKET_SCORE_WEIGHTS

    weights: dict[str, Decimal] = {}
    for key, default_weight in _DEFAULT_MARKET_SCORE_WEIGHTS.items():
        raw = configured.get(key, default_weight)
        try:
            weight = Decimal(str(raw))
        except (InvalidOperation, ValueError, TypeError):
            weight = default_weight
        weights[key] = weight if weight > Decimal("0") else default_weight

    total = sum(weights.values(), Decimal("0"))
    if total <= Decimal("0"):
        return _DEFAULT_MARKET_SCORE_WEIGHTS
    return weights


def score_market(snapshot: MarketSnapshot | None) -> Decimal:
    """Compute composite market score in the range 0-100.

    Args:
        snapshot: Market snapshot to score. ``None`` is rejected.

    Returns:
        Composite score in [0, 100], or ``Decimal("0")`` when all signals are missing.

    Raises:
        ValueError: If ``snapshot`` is ``None``.
    """
    if snapshot is None:
        raise ValueError("snapshot cannot be None")

    weights = _get_market_score_weights()
    weighted_total = Decimal("0")
    active_weight_total = Decimal("0")

    if snapshot.price_to_rent_ratio is not None:
        weighted_total += (
            normalize_market_price_to_rent_score(snapshot.price_to_rent_ratio)
            * weights["price_to_rent"]
        )
        active_weight_total += weights["price_to_rent"]

    if snapshot.population_growth_rate is not None:
        weighted_total += (
            normalize_market_growth_rate_score(snapshot.population_growth_rate)
            * weights["population_growth"]
        )
        active_weight_total += weights["population_growth"]

    if snapshot.employment_diversity_score is not None:
        weighted_total += (
            clamp_market_score(snapshot.employment_diversity_score)
            * weights["employment_diversity"]
        )
        active_weight_total += weights["employment_diversity"]

    if snapshot.landlord_friendliness_score is not None:
        weighted_total += (
            clamp_market_score(snapshot.landlord_friendliness_score)
            * weights["landlord_friendliness"]
        )
        active_weight_total += weights["landlord_friendliness"]

    if snapshot.rent_growth_rate is not None:
        weighted_total += (
            normalize_market_growth_rate_score(snapshot.rent_growth_rate)
            * weights["rent_growth"]
        )
        active_weight_total += weights["rent_growth"]

    if active_weight_total == Decimal("0"):
        return Decimal("0")

    return clamp_market_score(
        (weighted_total / active_weight_total).quantize(Decimal("0.01"))
    )


def update_market_scores(zip_codes: list[str]) -> int:
    """Recompute and persist market scores for existing snapshots."""
    if not zip_codes:
        return 0

    snapshots = list(MarketSnapshot.objects.filter(zip_code__in=zip_codes))
    for snapshot in snapshots:
        snapshot.market_score = score_market(snapshot)

    if snapshots:
        MarketSnapshot.objects.bulk_update(snapshots, ["market_score"])

    return len(snapshots)
