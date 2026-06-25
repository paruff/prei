"""BRRRR (Buy, Rehab, Rent, Refinance, Repeat) deal analysis service.

This module provides two levels of BRRRR analysis:

1. **Pure-math calculator** (``calculate_brrrr``): Takes raw Decimal inputs,
   computes the ``BRRRRAnalysis`` dataclass.  No database or Django dependency.
   Usable from a standalone calculator page or from tests.

2. **Django-aware orchestrator** (``analyze_brrrr_deal``): Fetches data from
   the database, reads ``settings.REHAB_COST_PER_SQFT``, and assembles the
   final result dict.  Delegates all financial math to pure functions in
   ``investor_app.finance.utils``.

Usage::

    from core.services.brrrr import calculate_brrrr, BRRRRAnalysis

    result = calculate_brrrr(
        purchase_price=Decimal("80000"),
        rehab_cost=Decimal("20000"),
        arv=Decimal("150000"),
        monthly_rent_post_rehab=Decimal("1200"),
        annual_operating_expenses=Decimal("3600"),
    )
    print(result.verdict)  # "Full Cycle" / "Partial Recycle" / "Capital Trap"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

from core.models import Listing
from investor_app.finance.utils import (
    brrrr_coc_return,
    calculate_monthly_mortgage,
    cash_left_in_deal,
    dscr,
    estimate_arv,
    estimate_rehab_cost,
    max_refinance_loan,
    noi,
    to_decimal,
)

logger = logging.getLogger(__name__)

# Standard cash-out refinance LTV for conventional investment properties (Fannie Mae).
_DEFAULT_LTV = Decimal("0.75")

# DSCR threshold used by most lenders for investment-property refinancing.
# Configurable via settings.FINANCE_DEFAULTS["brrrr_dscr_threshold"] (env: BRRRR_DSCR_THRESHOLD).
# Fannie Mae / conventional lenders typically require >= 1.25; some require 1.15–1.30.
DSCR_LENDER_THRESHOLD = Decimal("1.25")


# ---------------------------------------------------------------------------
# Pure-math BRRRR calculator (no Django/DB dependency)
# ---------------------------------------------------------------------------


@dataclass
class BRRRRAnalysis:
    """Result of a BRRRR deal analysis.

    All monetary fields are ``Decimal`` to avoid floating-point rounding.
    """

    purchase_price: Decimal
    rehab_cost: Decimal
    arv: Decimal  # After-Repair Value (user estimate)
    total_project_cost: Decimal  # purchase + rehab + closing costs
    max_refi_loan: Decimal  # arv * refi_ltv_pct (typically 0.75)
    cash_left_in_deal: Decimal  # total_project_cost - max_refi_loan
    cash_out_at_refi: Decimal  # max_refi_loan - original_loan_payoff (if any)
    post_refi_dscr: Decimal  # NOI / new annual debt service
    post_refi_coc: Decimal  # annual cashflow / cash_left_in_deal
    is_full_cycle: bool  # True if cash_left_in_deal <= 0
    verdict: str  # "Full Cycle" / "Partial Recycle" / "Capital Trap"


def calculate_brrrr(
    purchase_price: Decimal,
    rehab_cost: Decimal,
    arv: Decimal,
    monthly_rent_post_rehab: Decimal,
    annual_operating_expenses: Decimal,
    refi_ltv_pct: Decimal = Decimal("0.75"),
    refi_interest_rate: Decimal = Decimal("0.07"),
    refi_term_years: int = 30,
    closing_costs_pct: Decimal = Decimal("0.02"),
) -> BRRRRAnalysis:
    """Calculate BRRRR deal metrics from raw inputs.

    This function is pure math — no database or Django settings dependency.
    Use it from the standalone calculator page, tests, or any caller that
    already has the input values.

    Args:
        purchase_price: Acquisition price.
        rehab_cost: Total renovation budget.
        arv: After-Repair Value (user-supplied estimate).
        monthly_rent_post_rehab: Expected monthly rent after renovation.
        annual_operating_expenses: Total annual operating expenses
            (taxes, insurance, management, maintenance, capex, vacancy).
        refi_ltv_pct: Loan-to-value for the cash-out refi (default 75%).
        refi_interest_rate: Annual interest rate for the refi loan.
        refi_term_years: Amortisation term in years.
        closing_costs_pct: Closing costs as a fraction of purchase_price.

    Returns:
        A ``BRRRRAnalysis`` dataclass with all computed fields.

    Verdict logic:
        - ``cash_left_in_deal <= 0``: **Full Cycle** (infinite returns — best case)
        - ``0 < cash_left_in_deal <= total_project_cost * 0.25``: **Partial Recycle**
        - ``cash_left_in_deal > total_project_cost * 0.25``: **Capital Trap**
    """
    pp = to_decimal(purchase_price)
    rehab = to_decimal(rehab_cost)
    arv_val = to_decimal(arv)
    rent = to_decimal(monthly_rent_post_rehab)
    opex = to_decimal(annual_operating_expenses)

    # ── Total project cost ────────────────────────────────────────────────
    closing_costs = (pp * to_decimal(closing_costs_pct)).quantize(Decimal("0.01"))
    total_project_cost = pp + rehab + closing_costs

    # ── Refinance ─────────────────────────────────────────────────────────
    max_refi = (arv_val * to_decimal(refi_ltv_pct)).quantize(Decimal("0.01"))
    cash_left = total_project_cost - max_refi
    cash_out = max_refi  # no existing loan payoff in this simplified model

    # ── Post-refi debt service ────────────────────────────────────────────
    monthly_mortgage = calculate_monthly_mortgage(
        max_refi, to_decimal(refi_interest_rate), refi_term_years
    )
    annual_debt_service = (monthly_mortgage * Decimal("12")).quantize(Decimal("0.01"))

    # ── NOI ───────────────────────────────────────────────────────────────
    annual_rent = rent * Decimal("12")
    annual_noi = annual_rent - opex

    # ── DSCR ──────────────────────────────────────────────────────────────
    post_refi_dscr_val = dscr(annual_noi, annual_debt_service)

    # ── Cash-on-Cash ──────────────────────────────────────────────────────
    annual_cashflow = annual_noi - annual_debt_service
    post_refi_coc_val = brrrr_coc_return(annual_cashflow, cash_left)

    # ── Full-cycle flag ───────────────────────────────────────────────────
    is_full_cycle = cash_left <= Decimal("0")

    # ── Verdict ───────────────────────────────────────────────────────────
    if is_full_cycle:
        verdict = "Full Cycle"
    elif total_project_cost > 0 and cash_left <= total_project_cost * Decimal("0.25"):
        verdict = "Partial Recycle"
    else:
        verdict = "Capital Trap"

    return BRRRRAnalysis(
        purchase_price=pp,
        rehab_cost=rehab,
        arv=arv_val,
        total_project_cost=total_project_cost,
        max_refi_loan=max_refi,
        cash_left_in_deal=cash_left,
        cash_out_at_refi=cash_out,
        post_refi_dscr=post_refi_dscr_val,
        post_refi_coc=post_refi_coc_val,
        is_full_cycle=is_full_cycle,
        verdict=verdict,
    )


# ---------------------------------------------------------------------------
# Django-aware orchestrator (database-backed)
# ---------------------------------------------------------------------------


def analyze_brrrr_deal(
    listing_id: int,
    renovation_level: str,
    comparable_listing_ids: list[int],
) -> dict:
    """Analyse whether a distressed property can support a BRRRR strategy.

    Fetches the subject listing and each comparable from the database, then
    delegates all financial math to pure functions in ``finance/utils.py``.

    Args:
        listing_id: Primary key of the ``Listing`` to evaluate.
        renovation_level: Scope of renovation — must be one of ``"cosmetic"``,
            ``"moderate"``, or ``"full_gut"``.
        comparable_listing_ids: List of ``Listing`` PKs whose sold prices and
            square footages are used to estimate ARV.

    Returns:
        A dict with the following keys:

        * ``arv`` (Decimal): After-Repair Value estimate.
        * ``rehab_cost`` (Decimal): Estimated rehabilitation cost.
        * ``max_refi_loan`` (Decimal): Maximum cash-out refinance loan at 75 % LTV.
        * ``cash_left_in_deal`` (Decimal): Capital still deployed after the refi.
          Negative or zero signals "infinite CoC".
        * ``infinite_coc`` (bool): ``True`` if the investor recouped all capital.
        * ``post_refi_dscr`` (Decimal): DSCR for the new (post-refi) loan.
        * ``post_refi_dscr_passes`` (bool): ``True`` if DSCR ≥ 1.25.
        * ``monthly_cash_flow_post_refi`` (Decimal): Monthly cash flow after the
          refinanced mortgage payment.
        * ``coc_return`` (Decimal): Cash-on-Cash return (``Decimal("Infinity")``
          for infinite CoC).

    Raises:
        Listing.DoesNotExist: If ``listing_id`` or any comparable ID is not found.
        ValueError: If the subject listing has no price or square footage, or if
            no valid comparables can be built.
    """
    subject = Listing.objects.get(pk=listing_id)

    if not subject.price or subject.price <= 0:
        raise ValueError(f"Listing {listing_id} has no valid price for BRRRR analysis")
    if not subject.sq_ft or subject.sq_ft <= 0:
        raise ValueError(
            f"Listing {listing_id} has no valid square footage for BRRRR analysis"
        )

    # Build (price, sqft) tuples from comparables
    comparable_sales: list[tuple[Decimal, Decimal]] = []
    for comp_id in comparable_listing_ids:
        comp = Listing.objects.get(pk=comp_id)
        if comp.price and comp.price > 0 and comp.sq_ft and comp.sq_ft > 0:
            comparable_sales.append(
                (Decimal(str(comp.price)), Decimal(str(comp.sq_ft)))
            )
        else:
            logger.warning(
                "Comparable listing %d skipped: missing or non-positive price/sqft",
                comp_id,
            )

    if not comparable_sales:
        raise ValueError("No valid comparable listings found — cannot estimate ARV")

    purchase_price = Decimal(str(subject.price))
    subject_sqft = Decimal(str(subject.sq_ft))

    # Pull rehab cost schedule from settings (national averages; see settings.py)
    cost_per_sqft: dict[str, Decimal] = {
        k: Decimal(str(v)) for k, v in settings.REHAB_COST_PER_SQFT.items()
    }

    arv = estimate_arv(comparable_sales, subject_sqft)
    rehab_cost = estimate_rehab_cost(subject_sqft, renovation_level, cost_per_sqft)
    max_refi = max_refinance_loan(arv, _DEFAULT_LTV)
    cash_left = cash_left_in_deal(purchase_price, rehab_cost, max_refi)

    # Post-refi mortgage: use settings defaults for interest rate and term
    defaults = settings.FINANCE_DEFAULTS
    loan_interest_rate_pct = Decimal(str(defaults["loan_interest_rate_pct"]))
    loan_term_years = int(str(defaults["loan_term_years"]))
    vacancy_rate = Decimal(str(defaults["vacancy_rate"]))
    management_fee_rate = Decimal(str(defaults["management_fee_rate"]))
    capex_reserve_rate = Decimal(str(defaults["capex_reserve_rate"]))
    dscr_threshold = Decimal(str(defaults.get("brrrr_dscr_threshold", "1.25")))

    monthly_mortgage_post_refi = calculate_monthly_mortgage(
        max_refi, loan_interest_rate_pct, loan_term_years
    )
    annual_debt_service_post_refi = monthly_mortgage_post_refi * Decimal("12")

    # Estimate monthly rent using the 1 % rule on ARV as a conservative proxy.
    # This is a rough heuristic (typical range: 0.5 %–2 % depending on market
    # and property value). Actual rent should be verified against market data
    # before relying on this figure for underwriting decisions.
    monthly_rent = arv * Decimal("0.01")
    effective_monthly_income = monthly_rent * (Decimal("1") - vacancy_rate)
    monthly_expenses = monthly_rent * (management_fee_rate + capex_reserve_rate)

    annual_noi = noi(effective_monthly_income, monthly_expenses)
    post_refi_dscr = dscr(annual_noi, annual_debt_service_post_refi)

    annual_cash_flow_post_refi = annual_noi - annual_debt_service_post_refi
    monthly_cash_flow_post_refi = annual_cash_flow_post_refi / Decimal("12")

    coc = brrrr_coc_return(annual_cash_flow_post_refi, cash_left)
    infinite_coc = cash_left <= Decimal("0")

    return {
        "arv": arv,
        "rehab_cost": rehab_cost,
        "max_refi_loan": max_refi,
        "cash_left_in_deal": cash_left,
        "infinite_coc": infinite_coc,
        "post_refi_dscr": post_refi_dscr,
        "post_refi_dscr_passes": post_refi_dscr >= dscr_threshold,
        "monthly_cash_flow_post_refi": monthly_cash_flow_post_refi,
        "coc_return": coc,
    }
