"""Offer stage handler — offer price optimization and strategy.

Computes the optimal offer price for a property based on underwriting
results, market conditions, and investment strategy parameters.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OfferStrategy(str, Enum):
    """Offer pricing strategy variants."""

    CONSERVATIVE = "conservative"  # Offer below MAO (buffer for negotiation)
    TARGET = "target"  # Offer at MAO
    AGGRESSIVE = "aggressive"  # Offer above MAO (competitive market)


class OfferInput(BaseModel):
    """Input parameters for the offer solver."""

    mao: float = Field(..., description="Max Allowable Offer from underwriting")
    arv: Optional[float] = Field(
        default=None, description="After Repair Value (estimated resale value)"
    )
    rehab_budget: float = Field(default=0.0, ge=0)
    desired_equity: float = Field(
        default=0.0,
        ge=0,
        le=1.0,
        description="Minimum desired equity percentage (e.g. 0.20 = 20%)",
    )
    competition_multiplier: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Market competition factor (1.0 = neutral, >1 = hot market)",
    )


class OfferMetrics(BaseModel):
    """Output metrics from the offer solver."""

    offer_price: float
    strategy: OfferStrategy
    premium_over_mao: float
    premium_pct: float
    estimated_equity: Optional[float] = None
    estimated_equity_pct: Optional[float] = None


def solve_offer(
    inputs: OfferInput,
    strategy: OfferStrategy = OfferStrategy.TARGET,
) -> OfferMetrics:
    """Compute the optimal offer price based on strategy.

    Strategy rules:
        CONSERVATIVE: offer = MAO × 0.95 × competition_multiplier
        TARGET:       offer = MAO × competition_multiplier
        AGGRESSIVE:   offer = MAO × 1.05 × competition_multiplier

    All strategies clamp the offer to ensure minimum desired equity
    is maintained when ARV is known.

    Args:
        inputs: OfferInput with MAO, ARV, rehab, equity target.
        strategy: Pricing strategy enum.

    Returns:
        OfferMetrics with offer price and equity analysis.
    """
    # ── Base offer by strategy ────────────────────────────────────────────────
    if strategy == OfferStrategy.CONSERVATIVE:
        raw_offer = inputs.mao * 0.95
    elif strategy == OfferStrategy.AGGRESSIVE:
        raw_offer = inputs.mao * 1.05
    else:
        raw_offer = inputs.mao

    offer_price = raw_offer * inputs.competition_multiplier

    # ── Equity constraint (when ARV is known) ────────────────────────────────
    estimated_equity: Optional[float] = None
    estimated_equity_pct: Optional[float] = None

    if inputs.arv and inputs.arv > 0:
        total_cost = offer_price + inputs.rehab_budget
        estimated_equity = inputs.arv - total_cost
        estimated_equity_pct = estimated_equity / inputs.arv if inputs.arv > 0 else 0.0

        # Clamp offer to maintain minimum desired equity
        if inputs.desired_equity > 0:
            max_offer_for_equity = (
                inputs.arv * (1 - inputs.desired_equity) - inputs.rehab_budget
            )
            if max_offer_for_equity < offer_price:
                offer_price = max_offer_for_equity
                # Recalculate with clamped price
                total_cost = offer_price + inputs.rehab_budget
                estimated_equity = inputs.arv - total_cost
                estimated_equity_pct = (
                    estimated_equity / inputs.arv if inputs.arv > 0 else 0.0
                )

    premium = offer_price - inputs.mao
    premium_pct = premium / inputs.mao if inputs.mao > 0 else 0.0

    return OfferMetrics(
        offer_price=round(offer_price, 2),
        strategy=strategy,
        premium_over_mao=round(premium, 2),
        premium_pct=round(premium_pct, 6),
        estimated_equity=round(estimated_equity, 2)
        if estimated_equity is not None
        else None,
        estimated_equity_pct=round(estimated_equity_pct, 4)
        if estimated_equity_pct is not None
        else None,
    )
