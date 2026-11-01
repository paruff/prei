from __future__ import annotations

import logging
from decimal import Decimal
from typing import Iterable, Tuple

from django.conf import settings

from core.models import Listing, MarketSnapshot
from investor_app.finance.mortgage import calculate_monthly_mortgage
from investor_app.finance.utils import cap_rate, cash_on_cash, dscr

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

    if market_snapshot and market_snapshot.rent_index > 0:
        monthly_rent = Decimal(str(market_snapshot.rent_index))
    else:
        monthly_rent = price * Decimal("0.01")
    return estimate_kpis(price, monthly_rent)


def estimate_kpis(
    price: Decimal,
    monthly_rent: Decimal,
    estimates: dict[str, Decimal | None] | None = None,
) -> dict[str, Decimal]:
    """Cap rate, cash-on-cash, DSCR and NOI for a price and monthly rent.

    ``estimates`` are the stored underwriting rates (``expense_estimates``
    keys); omitted, they come from ``settings.FINANCE_DEFAULTS``. NOI comes
    from ``portfolio.annual_noi``, the same formula an acquired property uses.
    """
    from core.services.pipeline import expense_estimates
    from core.services.portfolio import annual_noi

    defaults = settings.FINANCE_DEFAULTS
    est = estimates if estimates is not None else expense_estimates(price)
    down_payment_rate = Decimal(str(defaults["down_payment_rate"]))
    loan_interest_rate_pct = Decimal(str(defaults["loan_interest_rate_pct"]))
    loan_term_years = int(str(defaults["loan_term_years"]))

    zero = Decimal("0")
    noi_annual = annual_noi(
        monthly_rent=monthly_rent,
        vacancy_rate=est["estimated_vacancy_rate"] or zero,
        mgmt_fee_pct=est["estimated_mgmt_fee_pct"] or zero,
        taxes_annual=est["estimated_taxes_annual"] or zero,
        insurance_annual=est["estimated_insurance_annual"] or zero,
        maintenance_monthly=Decimal(str(defaults["maintenance_monthly"])),
        capex_monthly=(
            monthly_rent * (est["estimated_capex_reserve_rate"] or zero)
        ).quantize(Decimal("0.01")),
    )
    cap_rate_val = cap_rate(noi_annual, price)

    down_payment = price * down_payment_rate
    loan_amount = price - down_payment
    monthly_mortgage = calculate_monthly_mortgage(
        loan_amount, loan_interest_rate_pct, loan_term_years
    )
    annual_debt_service = monthly_mortgage * Decimal("12")
    annual_cash_flow = noi_annual - annual_debt_service
    coc_val = cash_on_cash(annual_cash_flow, down_payment)
    dscr_val = dscr(noi_annual, annual_debt_service)

    return {
        "cap_rate": cap_rate_val,
        "cash_on_cash": coc_val,
        "dscr": dscr_val,
        "noi": noi_annual,
    }
