"""Offer stage handler — offer price optimization and strategy.

Ported from prei.pipeline.handlers.offer (pydantic removed, floats replaced
with Decimal — resolves LIMIT-21). Computes the optimal offer price for a
property based on underwriting results, market conditions, and investment
strategy parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from investor_app.finance.utils import to_decimal


class OfferStrategy(str, Enum):
    """Offer pricing strategy variants."""

    CONSERVATIVE = "conservative"  # Offer below MAO (buffer for negotiation)
    TARGET = "target"  # Offer at MAO
    AGGRESSIVE = "aggressive"  # Offer above MAO (competitive market)


@dataclass
class OfferInput:
    """Input parameters for the offer solver.

    All monetary values are Decimal dollars. desired_equity and
    competition_multiplier are fractions.
    """

    mao: Decimal
    arv: Decimal | None = None
    rehab_budget: Decimal = Decimal("0")
    desired_equity: Decimal = Decimal("0.0")
    competition_multiplier: Decimal = Decimal("1.0")

    def __post_init__(self) -> None:
        self.mao = to_decimal(self.mao)
        if self.mao <= 0:
            raise ValueError("mao must be > 0")
        if self.arv is not None:
            self.arv = to_decimal(self.arv)
        self.rehab_budget = to_decimal(self.rehab_budget)
        if self.rehab_budget < 0:
            raise ValueError("rehab_budget must be >= 0")
        self.desired_equity = to_decimal(self.desired_equity)
        if not Decimal("0") <= self.desired_equity <= Decimal("1"):
            raise ValueError("desired_equity must be in [0, 1]")
        self.competition_multiplier = to_decimal(self.competition_multiplier)
        if not Decimal("0.5") <= self.competition_multiplier <= Decimal("2.0"):
            raise ValueError("competition_multiplier must be in [0.5, 2.0]")


@dataclass
class OfferMetrics:
    """Output metrics from the offer solver."""

    offer_price: Decimal
    strategy: OfferStrategy
    premium_over_mao: Decimal
    premium_pct: Decimal
    estimated_equity: Decimal | None = None
    estimated_equity_pct: Decimal | None = None


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
        raw_offer = inputs.mao * Decimal("0.95")
    elif strategy == OfferStrategy.AGGRESSIVE:
        raw_offer = inputs.mao * Decimal("1.05")
    else:
        raw_offer = inputs.mao

    offer_price = raw_offer * inputs.competition_multiplier

    # ── Equity constraint (when ARV is known) ────────────────────────────────
    estimated_equity: Decimal | None = None
    estimated_equity_pct: Decimal | None = None

    if inputs.arv is not None and inputs.arv > 0:
        total_cost = offer_price + inputs.rehab_budget
        estimated_equity = inputs.arv - total_cost
        estimated_equity_pct = (
            estimated_equity / inputs.arv if inputs.arv > 0 else Decimal("0.0")
        )

        # Clamp offer to maintain minimum desired equity
        if inputs.desired_equity > 0:
            max_offer_for_equity = (
                inputs.arv * (Decimal("1") - inputs.desired_equity)
                - inputs.rehab_budget
            )
            if max_offer_for_equity < offer_price:
                offer_price = max_offer_for_equity
                # Recalculate with clamped price
                total_cost = offer_price + inputs.rehab_budget
                estimated_equity = inputs.arv - total_cost
                estimated_equity_pct = (
                    estimated_equity / inputs.arv if inputs.arv > 0 else Decimal("0.0")
                )

    premium = offer_price - inputs.mao
    premium_pct = premium / inputs.mao if inputs.mao > 0 else Decimal("0.0")

    return OfferMetrics(
        offer_price=offer_price.quantize(Decimal("0.01")),
        strategy=strategy,
        premium_over_mao=premium.quantize(Decimal("0.01")),
        premium_pct=premium_pct.quantize(Decimal("0.000001")),
        estimated_equity=estimated_equity.quantize(Decimal("0.01"))
        if estimated_equity is not None
        else None,
        estimated_equity_pct=estimated_equity_pct.quantize(Decimal("0.0001"))
        if estimated_equity_pct is not None
        else None,
    )
