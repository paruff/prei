"""Financial underwriting solver engine for the property pipeline.

Computes institutional performance indicators: NOI, Cap Rate, Cash-on-Cash
Yield, and Max Allowable Offer (MAO). Includes an optimization solver that
backsolves for purchase price given a target cap rate.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from investor_app.finance.utils import cap_rate, cash_on_cash, to_decimal

# ── Data models ───────────────────────────────────────────────────────────────


class UnderwritingInput(BaseModel):
    """Input parameters for the underwriting solver.

    All monetary values are Decimal dollars. Rate fields are fractions.
    """

    purchase_price: Decimal
    estimated_rent: Decimal
    vacancy_rate: Decimal = Decimal("0.05")  # Default 5%
    rehab_budget: Decimal = Decimal("0")
    property_tax_annual: Decimal
    insurance_annual: Decimal
    maintenance_reserve_rate: Decimal = Decimal("0.10")  # 10% of gross rent
    management_fee_rate: Decimal = Decimal("0.08")  # 8% of EGI
    hoa_annual: Decimal = Decimal("0")


class UnderwritingMetrics(BaseModel):
    """Output metrics from the underwriting solver."""

    noi: Decimal
    cap_rate: Decimal
    cash_on_cash: Decimal
    mao: Decimal


# ── Pure arithmetic helpers ────────────────────────────────────────────────────


def gross_potential_rent(estimated_rent: Decimal) -> Decimal:
    """Compute Gross Potential Rent (annual).

    GPR = estimated_monthly_rent x 12
    """
    return to_decimal(estimated_rent) * Decimal(12)


def effective_gross_income(gpr: Decimal, vacancy_rate: Decimal) -> Decimal:
    """Compute Effective Gross Income.

    EGI = GPR x (1 - vacancy_rate)
    """
    return to_decimal(gpr) * (Decimal("1") - to_decimal(vacancy_rate))


def total_operating_expenses(
    property_tax_annual: Decimal,
    insurance_annual: Decimal,
    gpr: Decimal,
    maintenance_reserve_rate: Decimal,
    egi: Decimal,
    management_fee_rate: Decimal,
    hoa_annual: Decimal,
) -> Decimal:
    """Compute total annual operating expenses.

    Operating Expenses = Property Taxes + Insurance + Maintenance Reserve
                        + Property Management Fees + HOA

    Maintenance Reserve = GPR x maintenance_reserve_rate
    Management Fees = EGI x management_fee_rate
    """
    maintenance = to_decimal(gpr) * to_decimal(maintenance_reserve_rate)
    management = to_decimal(egi) * to_decimal(management_fee_rate)
    return (
        to_decimal(property_tax_annual)
        + to_decimal(insurance_annual)
        + maintenance
        + management
        + to_decimal(hoa_annual)
    )


def net_operating_income(egi: Decimal, opex: Decimal) -> Decimal:
    """Compute Net Operating Income.

    NOI = EGI - Operating Expenses
    """
    return to_decimal(egi) - to_decimal(opex)


def cash_on_cash_yield(
    noi: Decimal, purchase_price: Decimal, rehab_budget: Decimal
) -> Decimal:
    """Compute Cash-on-Cash Yield (all-cash baseline).

    CoC = NOI / (Purchase Price + Rehab Budget)

    Delegates the division to investor_app.finance.utils.cash_on_cash (which
    already returns Decimal("0") when the denominator is zero) rather than
    reimplementing it locally. This is deliberately *not* a call to that
    module's true leveraged cash-on-cash metric conceptually - no debt
    service is netted out of ``noi`` here, since this models an all-cash
    acquisition yield (NOI over total cash outlay) rather than the return on
    an investor's equity after financing.
    """
    initial_cash = to_decimal(purchase_price) + to_decimal(rehab_budget)
    return cash_on_cash(to_decimal(noi), initial_cash)


def max_allowable_offer(noi: Decimal, target_cap_rate: Decimal | float) -> Decimal:
    """Solve for Max Allowable Offer given a target cap rate.

    MAO = NOI / Target Cap Rate

    Returns Decimal("0") if target_cap_rate <= 0.
    """
    rate = to_decimal(target_cap_rate)
    if rate <= 0:
        return Decimal("0")
    return to_decimal(noi) / rate


# ── Composition solver ────────────────────────────────────────────────────────


def solve_underwriting(
    inputs: UnderwritingInput,
    target_cap_rate: Decimal | float,
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
        noi=noi.quantize(Decimal("0.01")),
        cap_rate=cap.quantize(Decimal("0.000001")),
        cash_on_cash=coc.quantize(Decimal("0.000001")),
        mao=mao.quantize(Decimal("0.01")),
    )
