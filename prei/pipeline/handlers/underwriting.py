"""Financial underwriting solver engine for the property pipeline.

Computes institutional performance indicators: NOI, Cap Rate, Cash-on-Cash
Yield, and Max Allowable Offer (MAO). Includes an optimization solver that
backsolves for purchase price given a target cap rate.
"""

from __future__ import annotations

from pydantic import BaseModel


# ── Data models ───────────────────────────────────────────────────────────────


class UnderwritingInput(BaseModel):
    """Input parameters for the underwriting solver.

    All monetary values are in dollars (float). Rate fields are fractions.
    """

    purchase_price: float
    estimated_rent: float
    vacancy_rate: float = 0.05  # Default 5%
    rehab_budget: float = 0.0
    property_tax_annual: float
    insurance_annual: float
    maintenance_reserve_rate: float = 0.10  # 10% of gross rent
    management_fee_rate: float = 0.08  # 8% of EGI
    hoa_annual: float = 0.0


class UnderwritingMetrics(BaseModel):
    """Output metrics from the underwriting solver."""

    noi: float
    cap_rate: float
    cash_on_cash: float
    mao: float


# ── Pure arithmetic helpers ────────────────────────────────────────────────────


def gross_potential_rent(estimated_rent: float) -> float:
    """Compute Gross Potential Rent (annual).

    GPR = estimated_monthly_rent × 12
    """
    return estimated_rent * 12.0


def effective_gross_income(gpr: float, vacancy_rate: float) -> float:
    """Compute Effective Gross Income.

    EGI = GPR × (1 - vacancy_rate)
    """
    return gpr * (1.0 - vacancy_rate)


def total_operating_expenses(
    property_tax_annual: float,
    insurance_annual: float,
    gpr: float,
    maintenance_reserve_rate: float,
    egi: float,
    management_fee_rate: float,
    hoa_annual: float,
) -> float:
    """Compute total annual operating expenses.

    Operating Expenses = Property Taxes + Insurance + Maintenance Reserve
                        + Property Management Fees + HOA

    Maintenance Reserve = GPR × maintenance_reserve_rate
    Management Fees = EGI × management_fee_rate
    """
    maintenance = gpr * maintenance_reserve_rate
    management = egi * management_fee_rate
    return (
        property_tax_annual + insurance_annual + maintenance + management + hoa_annual
    )


def net_operating_income(egi: float, opex: float) -> float:
    """Compute Net Operating Income.

    NOI = EGI - Operating Expenses
    """
    return egi - opex


def cap_rate(noi: float, purchase_price: float) -> float:
    """Compute Capitalization Rate.

    Cap Rate = NOI / Purchase Price

    Returns 0.0 if purchase_price <= 0 to avoid division by zero.
    """
    if purchase_price <= 0:
        return 0.0
    return noi / purchase_price


def cash_on_cash_yield(noi: float, purchase_price: float, rehab_budget: float) -> float:
    """Compute Cash-on-Cash Yield (all-cash baseline).

    CoC = NOI / (Purchase Price + Rehab Budget)

    Returns 0.0 if initial cash outlay <= 0.
    """
    initial_cash = purchase_price + rehab_budget
    if initial_cash <= 0:
        return 0.0
    return noi / initial_cash


def max_allowable_offer(noi: float, target_cap_rate: float) -> float:
    """Solve for Max Allowable Offer given a target cap rate.

    MAO = NOI / Target Cap Rate

    Returns 0.0 if target_cap_rate <= 0.
    """
    if target_cap_rate <= 0:
        return 0.0
    return noi / target_cap_rate


# ── Composition solver ────────────────────────────────────────────────────────


def solve_underwriting(
    inputs: UnderwritingInput,
    target_cap_rate: float,
) -> UnderwritingMetrics:
    """Compute all underwriting metrics and solve for MAO.

    Evaluation order:
      1. Gross Potential Rent (GPR)
      2. Effective Gross Income (EGI)
      3. Operating Expenses
      4. Net Operating Income (NOI)
      5. Cap Rate = NOI / Purchase Price
      6. Cash-on-Cash = NOI / (Price + Rehab)
      7. Max Allowable Offer = NOI / Target Cap Rate

    Args:
        inputs: UnderwritingInput with property financial data.
        target_cap_rate: Minimum acceptable cap rate (e.g., 0.08 for 8%).

    Returns:
        UnderwritingMetrics with all computed values.
    """
    # ── 1. Income ─────────────────────────────────────────────────────────
    gpr = gross_potential_rent(inputs.estimated_rent)
    egi = effective_gross_income(gpr, inputs.vacancy_rate)

    # ── 2. Expenses ───────────────────────────────────────────────────────
    opex = total_operating_expenses(
        property_tax_annual=inputs.property_tax_annual,
        insurance_annual=inputs.insurance_annual,
        gpr=gpr,
        maintenance_reserve_rate=inputs.maintenance_reserve_rate,
        egi=egi,
        management_fee_rate=inputs.management_fee_rate,
        hoa_annual=inputs.hoa_annual,
    )

    # ── 3. NOI ────────────────────────────────────────────────────────────
    noi = net_operating_income(egi, opex)

    # ── 4. Returns ────────────────────────────────────────────────────────
    cap = cap_rate(noi, inputs.purchase_price)
    coc = cash_on_cash_yield(noi, inputs.purchase_price, inputs.rehab_budget)

    # ── 5. MAO (backsolve) ────────────────────────────────────────────────
    mao = max_allowable_offer(noi, target_cap_rate)

    return UnderwritingMetrics(
        noi=round(noi, 2),
        cap_rate=round(cap, 6),
        cash_on_cash=round(coc, 6),
        mao=round(mao, 2),
    )
