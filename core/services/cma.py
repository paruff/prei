from __future__ import annotations

import logging
from decimal import Decimal
from typing import Iterable, Tuple

from django.conf import settings

from core.models import Listing, MarketSnapshot
from investor_app.finance.utils import (
    calculate_monthly_mortgage,
    cap_rate,
    cash_on_cash,
    dscr,
    noi,
)

logger = logging.getLogger(__name__)


def price_per_sqft(listing: Listing) -> Decimal:
    if not listing.sq_ft:
        return Decimal("0")
    return Decimal(listing.price) / Decimal(listing.sq_ft)


def find_undervalued(
    listings: Iterable[Listing], threshold: Decimal = Decimal("0.85")
) -> Iterable[Tuple[Listing, Decimal]]:
    """Return listings where PPSF is below the median * threshold.

    This is a simple CMA placeholder; later integrate comps API.
    """
    ppsf_values = [price_per_sqft(listing) for listing in listings if listing.sq_ft]
    if not ppsf_values:
        return []
    # median approximation
    sorted_vals = sorted(ppsf_values)
    mid = len(sorted_vals) // 2
    median = (
        sorted_vals[mid]
        if len(sorted_vals) % 2 == 1
        else (sorted_vals[mid - 1] + sorted_vals[mid]) / Decimal(2)
    )
    cutoff = median * threshold
    results = []
    for listing in listings:
        ppsf = price_per_sqft(listing)
        if ppsf and ppsf < cutoff:
            results.append((listing, ppsf))
    return results


def estimate_listing_kpis(
    listing: Listing, market_snapshot: MarketSnapshot | None
) -> dict[str, Decimal]:
    """Estimate investment KPIs for a listing using configured finance defaults.

    Uses ``settings.FINANCE_DEFAULTS`` for all rates.  If a ``MarketSnapshot``
    is provided and its ``rent_index`` is positive, that value is used as the
    monthly rent estimate; otherwise the 1 % rule (monthly rent = 1 % of
    purchase price) is applied as a fallback.

    Args:
        listing: The listing to evaluate.
        market_snapshot: Optional snapshot for the listing's ZIP code.

    Returns:
        A dict with keys ``cap_rate``, ``cash_on_cash``, ``dscr``, and ``noi``
        (all ``Decimal``).  Returns a dict of zeros if the listing price is
        missing or non-positive.
    """
    zero_kpis: dict[str, Decimal] = {
        "cap_rate": Decimal("0"),
        "cash_on_cash": Decimal("0"),
        "dscr": Decimal("0"),
        "noi": Decimal("0"),
    }

    price = Decimal(str(listing.price)) if listing.price else Decimal("0")
    if price <= 0:
        return zero_kpis

    defaults = settings.FINANCE_DEFAULTS
    vacancy_rate = Decimal(str(defaults["vacancy_rate"]))
    management_fee_rate = Decimal(str(defaults["management_fee_rate"]))
    capex_reserve_rate = Decimal(str(defaults["capex_reserve_rate"]))
    down_payment_rate = Decimal(str(defaults["down_payment_rate"]))
    loan_interest_rate_pct = Decimal(str(defaults["loan_interest_rate_pct"]))
    loan_term_years = int(str(defaults["loan_term_years"]))

    if market_snapshot and market_snapshot.rent_index > 0:
        monthly_rent = Decimal(str(market_snapshot.rent_index))
    else:
        monthly_rent = price * Decimal("0.01")

    effective_monthly_income = monthly_rent * (Decimal("1") - vacancy_rate)
    monthly_expenses = monthly_rent * (management_fee_rate + capex_reserve_rate)
    annual_noi = noi(effective_monthly_income, monthly_expenses)
    cap_rate_val = cap_rate(annual_noi, price)

    down_payment = price * down_payment_rate
    loan_amount = price - down_payment
    monthly_mortgage = calculate_monthly_mortgage(
        loan_amount, loan_interest_rate_pct, loan_term_years
    )
    annual_debt_service = monthly_mortgage * Decimal("12")
    annual_cash_flow = annual_noi - annual_debt_service
    coc_val = cash_on_cash(annual_cash_flow, down_payment)
    dscr_val = dscr(annual_noi, annual_debt_service)

    return {
        "cap_rate": cap_rate_val,
        "cash_on_cash": coc_val,
        "dscr": dscr_val,
        "noi": annual_noi,
    }
