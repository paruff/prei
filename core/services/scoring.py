"""Investor-grade underwriting score (v2).

score_listing_v2 replaces the v1 PPSF+freshness heuristic with a weighted
scoring model based on the criteria passive real-estate investors use:
1% Rule, Cash-on-Cash, DSCR, Cap Rate, GRM, and After-Tax CoC.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP


def _q2(val: Decimal) -> Decimal:
    """Quantize to 2 decimal places."""
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _q4(val: Decimal) -> Decimal:
    """Quantize to 4 decimal places."""
    return val.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class UnderwritingScore:
    """Result of score_listing_v2 — a full underwriting snapshot."""

    total_score: int  # 0–100
    passes_one_pct_rule: bool
    one_pct_ratio: Decimal  # monthly_rent / purchase_price
    cap_rate: Decimal
    cash_on_cash: Decimal
    dscr: Decimal
    grm: Decimal
    after_tax_coc: Decimal
    projected_irr: Decimal  # annualized IRR over target hold period
    verdict: str  # "Strong Buy" / "Conditional" / "Pass"
    flags: list[str] = field(default_factory=list)

    # Breakdown for transparency
    score_1pct: int = 0
    score_coc: int = 0
    score_dscr: int = 0
    score_cap: int = 0
    score_grm: int = 0
    score_after_tax: int = 0

    # ── Color-class properties ─────────────────────────────────────────────

    @property
    def coc_color_class(self) -> str:
        """Return CSS class based on Cash-on-Cash thresholds."""
        if self.cash_on_cash >= Decimal("0.08"):
            return "num-good"
        if self.cash_on_cash >= Decimal("0.05"):
            return "num-warn"
        return "num-bad"

    @property
    def cap_rate_color_class(self) -> str:
        """Return CSS class based on cap rate threshold."""
        return "num-good" if self.cap_rate >= Decimal("0.06") else "num-warn"

    @property
    def dscr_color_class(self) -> str:
        """Return CSS class based on DSCR threshold."""
        return "num-good" if self.dscr >= Decimal("1.25") else "num-bad"

    @property
    def grm_color_class(self) -> str:
        """Return CSS class based on GRM thresholds."""
        if self.grm <= Decimal("12"):
            return "num-good"
        if self.grm <= Decimal("16"):
            return "num-warn"
        return "num-bad"

    @property
    def verdict_label(self) -> str:
        """Human-readable verdict label."""
        return {
            "Strong Buy": "Strong Buy",
            "Conditional": "Conditional",
            "Pass": "Pass",
        }.get(self.verdict, self.verdict)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _monthly_mortgage(principal: Decimal, annual_rate: Decimal, years: int) -> Decimal:
    """Calculate monthly P+I payment."""
    if principal <= 0:
        return Decimal("0")
    monthly_rate = annual_rate / Decimal(12)
    if monthly_rate == 0:
        return principal / Decimal(years * 12)
    n = Decimal(years * 12)
    factor = (1 + monthly_rate) ** n
    return _q2(principal * monthly_rate * factor / (factor - 1))


# ── Core scoring function ─────────────────────────────────────────────────────


def score_listing_v2(property_obj, targets) -> UnderwritingScore:
    """Compute an investor-grade multi-signal underwriting score.

    Scoring weights:
        1% Rule pass        : 20 points
        CoC >= target       : 25 points (partial credit: actual/target * 25)
        DSCR >= target      : 20 points (partial credit)
        Cap rate >= 6%      : 15 points (partial credit)
        GRM <= target       : 10 points (partial credit)
        After-tax CoC bonus : 10 points

    Verdict:
        75–100 : "Strong Buy"
        50–74  : "Conditional"
        0–49   : "Pass"

    Args:
        property_obj: A core.models.Property instance.
        targets: A core.models.UserInvestmentTargets instance.

    Returns:
        UnderwritingScore with all fields populated.
    """
    from investor_app.finance.utils import (
        build_cashflows,
        calculate_annual_depreciation,
        calculate_after_tax_cashflow,
        irr as calc_irr,
    )
    from core.models import UserProfile

    pp = property_obj.purchase_price
    monthly_rent = property_obj.monthly_rent_gross
    annual_rent = monthly_rent * Decimal(12)

    # ── Derived values ────────────────────────────────────────────────────────
    vacancy_loss = annual_rent * property_obj.vacancy_rate
    effective_rent = annual_rent - vacancy_loss

    # Mortgage
    down_pmt = pp * property_obj.down_payment_pct
    loan_amount = pp - down_pmt
    monthly_pi = _monthly_mortgage(loan_amount, property_obj.interest_rate, property_obj.loan_term_years)
    annual_pi = monthly_pi * Decimal(12)

    # Operating expenses
    opex = (
        property_obj.property_taxes_annual
        + property_obj.insurance_annual
        + property_obj.hoa_monthly * Decimal(12)
        + property_obj.maintenance_monthly * Decimal(12)
        + property_obj.capex_monthly * Decimal(12)
    )
    # Management fee is % of effective gross income
    mgmt_fee = effective_rent * property_obj.mgmt_fee_pct
    total_expenses = opex + mgmt_fee
    annual_noi = effective_rent - total_expenses
    annual_debt_service = annual_pi

    # KPIs using utils functions
    from investor_app.finance.utils import (
        cap_rate as calc_cap_rate,
        cash_on_cash,
        dscr,
        gross_rent_multiplier,
    )

    cap = calc_cap_rate(annual_noi, pp)
    grm = gross_rent_multiplier(pp, annual_rent) if annual_rent > 0 else Decimal("999")

    # Cash-on-Cash = annual pre-tax cash flow / total cash invested
    annual_cash_flow = annual_noi - annual_pi
    coc = cash_on_cash(annual_cash_flow, down_pmt) if down_pmt > 0 else Decimal("0")

    # DSCR = annual NOI / annual debt service
    dscr_val = dscr(annual_noi, annual_pi) if annual_pi > 0 else Decimal("0")

    # One-percent rule
    one_pct_ratio = monthly_rent / pp if pp > 0 else Decimal("0")
    passes_1pct = one_pct_ratio >= Decimal("0.01")

    # After-tax cash flow
    try:
        user_profile = UserProfile.objects.get(user=property_obj.user)
        land_pct = user_profile.land_value_pct
    except UserProfile.DoesNotExist:
        land_pct = Decimal("0.20")
    deprec = calculate_annual_depreciation(pp, land_value_pct=land_pct)
    pre_tax_cf = annual_cash_flow
    after_tax = calculate_after_tax_cashflow(pre_tax_cf, deprec, targets.marginal_tax_rate)

    # Projected IRR via numpy_financial
    try:
        from core.models import InvestmentAnalysis

        analysis, _ = InvestmentAnalysis.objects.get_or_create(property=property_obj)
        hold_years = targets.target_hold_years or analysis.hold_years
        exit_cap_rate = analysis.exit_cap_rate or Decimal("0.06")
        monthly_noi_val = annual_noi / Decimal(12)
        flows = build_cashflows(
            purchase_price=pp,
            monthly_noi=monthly_noi_val,
            hold_years=hold_years,
            exit_cap_rate=exit_cap_rate,
        )
        monthly_irr = calc_irr(flows)
        if monthly_irr > 0:
            projected_irr = ((1 + monthly_irr) ** 12) - 1
        else:
            projected_irr = monthly_irr
    except Exception:
        projected_irr = Decimal("0")

    # ── Scoring ───────────────────────────────────────────────────────────────
    flags: list[str] = []

    # 1. One-percent rule (20 points)
    score_1pct = 20 if passes_1pct else 0
    if not passes_1pct:
        flags.append(f"Fails 1% Rule ({_q2(one_pct_ratio * 100):.2f}% vs 1.00%)")

    # 2. Cash-on-Cash (25 points, partial credit)
    target_coc = targets.min_coc_pct
    if target_coc > 0 and coc >= Decimal("0"):
        coc_ratio = min(coc / target_coc, Decimal("1"))
        score_coc = int((coc_ratio * Decimal(25)).to_integral_value(rounding=ROUND_HALF_UP))
    else:
        score_coc = 0
    if coc < target_coc:
        flags.append(f"CoC {coc * 100:.1f}% below target {target_coc * 100:.1f}%")
    if coc < Decimal("0"):
        flags.append("Negative Cash-on-Cash return")

    # 3. DSCR (20 points, partial credit)
    target_dscr = targets.min_dscr
    if target_dscr > 0 and dscr_val >= Decimal("0"):
        dscr_ratio = min(dscr_val / target_dscr, Decimal("1"))
        score_dscr = int((dscr_ratio * Decimal(20)).to_integral_value(rounding=ROUND_HALF_UP))
    else:
        score_dscr = 0
    if dscr_val < target_dscr:
        flags.append(f"DSCR {dscr_val:.2f} below target {target_dscr:.2f}")

    # 4. Cap rate (15 points, partial credit — target 6%)
    target_cap = Decimal("0.06")
    if cap > 0:
        cap_ratio = min(cap / target_cap, Decimal("1"))
        score_cap = int((cap_ratio * Decimal(15)).to_integral_value(rounding=ROUND_HALF_UP))
    else:
        score_cap = 0
    if cap < target_cap:
        flags.append(f"Cap rate {cap * 100:.1f}% below 6%")

    # 5. GRM (10 points, partial credit — lower is better)
    target_grm = targets.max_grm
    if target_grm > 0:
        if grm <= target_grm:
            score_grm = 10
        else:
            ratio = target_grm / grm
            score_grm = int((ratio * Decimal(10)).to_integral_value(rounding=ROUND_HALF_UP))
    else:
        score_grm = 0
    if grm > target_grm:
        flags.append(f"GRM {grm:.1f} exceeds target {target_grm:.1f}")

    # 6. After-tax CoC bonus (10 points)
    score_after_tax = 10 if after_tax > Decimal("0") else 0
    if after_tax <= Decimal("0"):
        flags.append("Negative after-tax cash flow")

    # ── Composite ─────────────────────────────────────────────────────────────
    total = score_1pct + score_coc + score_dscr + score_cap + score_grm + score_after_tax

    # Cap at 40 if 1% rule fails and require_one_pct_rule is set
    if targets.require_one_pct_rule and not passes_1pct and total > 40:
        total = 40

    total = max(0, min(100, total))

    # ── Verdict ───────────────────────────────────────────────────────────────
    if total >= 75:
        verdict = "Strong Buy"
    elif total >= 50:
        verdict = "Conditional"
    else:
        verdict = "Pass"

    return UnderwritingScore(
        total_score=total,
        passes_one_pct_rule=passes_1pct,
        one_pct_ratio=_q2(one_pct_ratio),
        cap_rate=_q4(cap),
        cash_on_cash=_q4(coc),
        dscr=_q4(dscr_val),
        grm=_q2(grm),
        after_tax_coc=_q2(after_tax),
        projected_irr=_q4(projected_irr),
        verdict=verdict,
        flags=flags,
        score_1pct=score_1pct,
        score_coc=score_coc,
        score_dscr=score_dscr,
        score_cap=score_cap,
        score_grm=score_grm,
        score_after_tax=score_after_tax,
    )


# ── Deprecated v1 wrapper ─────────────────────────────────────────────────────


def score_listing_v1_deprecated(*args, **kwargs):
    """Deprecated: use score_listing_v2 instead."""
    warnings.warn(
        "score_listing_v1 is deprecated and will be removed in a future release. "
        "Use core.services.scoring.score_listing_v2 for underwriting-grade scores.",
        DeprecationWarning,
        stacklevel=2,
    )
    from investor_app.finance.utils import score_listing_v1

    return score_listing_v1(*args, **kwargs)
