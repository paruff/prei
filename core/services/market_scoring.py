"""Market-level investor viability scoring service."""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from django.conf import settings

from core.models import MarketSnapshot

_DEFAULT_MARKET_SCORE_WEIGHTS: dict[str, Decimal] = {
    "price_to_rent": Decimal("0.25"),
    "population_growth": Decimal("0.20"),
    "employment_diversity": Decimal("0.20"),
    "landlord_friendliness": Decimal("0.25"),
    "rent_growth": Decimal("0.10"),
}


def _normalize_price_to_rent(price_to_rent: Decimal) -> Decimal:
    """Convert price-to-rent ratio into a 0-100 score."""
    if price_to_rent <= Decimal("0"):
        return Decimal("0")
    if price_to_rent < Decimal("15"):
        return Decimal("100")
    if price_to_rent <= Decimal("20"):
        return (Decimal("20") - price_to_rent) / Decimal("5") * Decimal("40") + Decimal(
            "60"
        )
    if price_to_rent <= Decimal("30"):
        return (Decimal("30") - price_to_rent) / Decimal("10") * Decimal("60")
    return Decimal("0")


def _normalize_growth_rate_percent(growth_rate: Decimal) -> Decimal:
    """Convert a percent growth rate into a 0-100 score."""
    clamped = max(Decimal("-5"), min(Decimal("10"), growth_rate))
    return (clamped + Decimal("5")) / Decimal("15") * Decimal("100")


def _clamp_score(value: Decimal) -> Decimal:
    """Clamp score to a valid 0-100 range."""
    return max(Decimal("0"), min(Decimal("100"), value))


def _get_market_score_weights() -> dict[str, Decimal]:
    """Return validated score weights from settings with safe defaults."""
    configured = getattr(settings, "MARKET_SCORE_WEIGHTS", None)
    if not isinstance(configured, Mapping):
        return _DEFAULT_MARKET_SCORE_WEIGHTS

    weights: dict[str, Decimal] = {}
    for key, default_weight in _DEFAULT_MARKET_SCORE_WEIGHTS.items():
        raw = configured.get(key, default_weight)
        weight = Decimal(str(raw))
        weights[key] = weight if weight > Decimal("0") else default_weight

    total = sum(weights.values(), Decimal("0"))
    if total <= Decimal("0"):
        return _DEFAULT_MARKET_SCORE_WEIGHTS
    return weights


def score_market(snapshot: MarketSnapshot) -> Decimal:
    """Compute composite market score in the range 0-100."""
    if snapshot is None:
        raise ValueError("snapshot cannot be None")

    weights = _get_market_score_weights()
    weighted_total = Decimal("0")
    active_weight_total = Decimal("0")

    if snapshot.price_to_rent_ratio is not None:
        weighted_total += (
            _normalize_price_to_rent(snapshot.price_to_rent_ratio)
            * weights["price_to_rent"]
        )
        active_weight_total += weights["price_to_rent"]

    if snapshot.population_growth_rate is not None:
        weighted_total += (
            _normalize_growth_rate_percent(snapshot.population_growth_rate)
            * weights["population_growth"]
        )
        active_weight_total += weights["population_growth"]

    if snapshot.employment_diversity_score is not None:
        weighted_total += (
            _clamp_score(snapshot.employment_diversity_score)
            * weights["employment_diversity"]
        )
        active_weight_total += weights["employment_diversity"]

    if snapshot.landlord_friendliness_score is not None:
        weighted_total += (
            _clamp_score(snapshot.landlord_friendliness_score)
            * weights["landlord_friendliness"]
        )
        active_weight_total += weights["landlord_friendliness"]

    if snapshot.rent_growth_rate is not None:
        weighted_total += (
            _normalize_growth_rate_percent(snapshot.rent_growth_rate)
            * weights["rent_growth"]
        )
        active_weight_total += weights["rent_growth"]

    if active_weight_total == Decimal("0"):
        return Decimal("0")

    return _clamp_score(
        (weighted_total / active_weight_total).quantize(Decimal("0.01"))
    )


def update_market_scores(zip_codes: list[str]) -> int:
    """Recompute and persist market scores for existing snapshots."""
    if not zip_codes:
        return 0

    updated = 0
    for snapshot in MarketSnapshot.objects.filter(zip_code__in=zip_codes):
        snapshot.market_score = score_market(snapshot)
        snapshot.save(update_fields=["market_score", "updated_at"])
        updated += 1

    return updated
