"""Financing scenario comparison service for analyzing loan products."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, TypedDict

from core.models import Property, FinancingScenario
from investor_app.finance.utils import noi, dscr, cash_on_cash, cap_rate
from investor_app.finance.mortgage import calculate_break_even_rent


@dataclass(frozen=True)
class ScenarioResult:
    """Result of a financing scenario analysis."""

    loan_type: str
    ltv_pct: Decimal
    interest_rate: Decimal
    term_years: int
    down_payment: Decimal
    monthly_payment: Decimal
    annual_debt_service: Decimal
    noi: Decimal
    cap_rate: Decimal
    cash_on_cash: Decimal
    dscr: Decimal
    breakeven_rent: Decimal
    monthly_cash_flow: Decimal
    total_cash_invested: Decimal
    closing_costs: Decimal


class DefaultScenarioDict(TypedDict):
    loan_type: str
    ltv_pct: Decimal
    interest_rate: Decimal
    term_years: int
    closing_costs: Decimal


DEFAULT_SCENARIOS: list[DefaultScenarioDict] = [
    {
        "loan_type": FinancingScenario.LoanType.CONVENTIONAL,
        "ltv_pct": Decimal("0.75"),
        "interest_rate": Decimal("0.075"),
        "term_years": 30,
        "closing_costs": Decimal("5000"),
    },
    {
        "loan_type": FinancingScenario.LoanType.DSCR,
        "ltv_pct": Decimal("0.80"),
        "interest_rate": Decimal("0.085"),
        "term_years": 30,
        "closing_costs": Decimal("7500"),
    },
    {
        "loan_type": FinancingScenario.LoanType.SELLER_FINANCING,
        "ltv_pct": Decimal("0.90"),
        "interest_rate": Decimal("0.06"),
        "term_years": 15,
        "closing_costs": Decimal("3000"),
    },
]


def get_or_create_default_scenarios(property: Property) -> List[FinancingScenario]:
    """Get or create the three default financing scenarios for a property."""
    scenarios = []
    for default in DEFAULT_SCENARIOS:
        scenario, created = FinancingScenario.objects.get_or_create(
            prop=property,
            loan_type=default["loan_type"],
            defaults={
                "ltv_pct": default["ltv_pct"],
                "interest_rate": default["interest_rate"],
                "term_years": default["term_years"],  # type: ignore[dict-item]
                "closing_costs": default["closing_costs"],  # type: ignore[dict-item]
            },
        )
        scenarios.append(scenario)
    return scenarios


def calculate_scenario_result(
    property: Property, scenario: FinancingScenario
) -> ScenarioResult:
    """Calculate all metrics for a single financing scenario."""

    # Monthly income and expenses (excluding debt service)
    monthly_income = Decimal(property.monthly_rent_gross) + Decimal(
        property.other_monthly_income
    )

    # Vacancy allowance
    vacancy_allowance = monthly_income * property.vacancy_rate
    effective_gross_income = monthly_income - vacancy_allowance

    # Operating expenses (excluding debt service)
    monthly_expenses = (
        Decimal(property.property_taxes_annual) / Decimal(12)
        + Decimal(property.insurance_annual) / Decimal(12)
        + Decimal(property.hoa_monthly)
        + Decimal(property.maintenance_monthly)
        + Decimal(property.capex_monthly)
        + effective_gross_income * property.mgmt_fee_pct
    )

    noi_annual = noi(effective_gross_income, monthly_expenses)

    # Cap rate
    cap_rate_val = cap_rate(noi_annual, property.purchase_price)

    # Monthly payment from scenario
    monthly_payment = scenario.monthly_payment
    annual_debt_service = scenario.annual_debt_service

    # DSCR
    dscr_val = dscr(noi_annual, annual_debt_service)

    # Cash-on-cash
    annual_cash_flow = noi_annual - annual_debt_service
    coc = cash_on_cash(annual_cash_flow, scenario.total_cash_invested)

    # Break-even rent
    break_even = calculate_break_even_rent(
        monthly_carrying_costs=monthly_expenses + monthly_payment,
        vacancy_rate_percent=property.vacancy_rate * Decimal(100),
        property_management_percent=property.mgmt_fee_pct * Decimal(100),
    )
    breakeven_rent = break_even["monthly"]

    # Monthly cash flow
    monthly_cash_flow = noi_annual / Decimal(12) - monthly_payment

    return ScenarioResult(
        loan_type=scenario.get_loan_type_display(),
        ltv_pct=scenario.ltv_pct,
        interest_rate=scenario.interest_rate,
        term_years=scenario.term_years,
        down_payment=scenario.down_payment,
        monthly_payment=monthly_payment,
        annual_debt_service=annual_debt_service,
        noi=noi_annual,
        cap_rate=cap_rate_val,
        cash_on_cash=coc,
        dscr=dscr_val,
        breakeven_rent=breakeven_rent,
        monthly_cash_flow=monthly_cash_flow,
        total_cash_invested=scenario.total_cash_invested,
        closing_costs=scenario.closing_costs,
    )


def compare_scenarios(property: Property) -> List[ScenarioResult]:
    """Compare all financing scenarios for a property.

    Args:
        property: Property to analyze.

    Returns:
        List of ScenarioResult sorted by loan_type order.
    """
    scenarios = get_or_create_default_scenarios(property)
    results = [calculate_scenario_result(property, scenario) for scenario in scenarios]

    # Sort by loan_type order: conventional, dscr, seller_financing
    order = {
        "Conventional": 0,
        "DSCR Loan": 1,
        "Seller Financing": 2,
        "Other": 3,
    }
    results.sort(key=lambda r: order.get(r.loan_type, 99))

    return results


def get_best_scenario(
    results: List[ScenarioResult], metric: str
) -> ScenarioResult | None:
    """Get the best scenario by a given metric.

    Args:
        results: List of scenario results.
        metric: Metric to optimize ("cash_on_cash" or "dscr").

    Returns:
        Best scenario or None if empty.
    """
    if not results:
        return None

    if metric == "cash_on_cash":
        return max(results, key=lambda r: r.cash_on_cash)
    elif metric == "dscr":
        return max(results, key=lambda r: r.dscr)
    else:
        raise ValueError(f"Unknown metric: {metric}")
