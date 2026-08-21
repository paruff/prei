"""Exit strategy modeling: hold-period projections across appreciation scenarios.

Generates a comparison table of exit outcomes across multiple hold periods
and appreciation scenarios so analysts can evaluate when and how to exit.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Any

from core.services.projections import (
    ExitAnalysis,
    project_hold_period,
)

if TYPE_CHECKING:
    from core.models import Property


# ── Default scenario grids ────────────────────────────────────────────────────

# Hold periods (years) to model exits at
DEFAULT_HOLD_PERIODS: list[int] = [3, 5, 7, 10, 15]

# Annual appreciation scenarios to test
DEFAULT_APPRECIATION_SCENARIOS: Dict[str, Decimal] = {
    "Pessimistic": Decimal("-0.01"),
    "Conservative": Decimal("0.02"),
    "Base": Decimal("0.03"),
    "Optimistic": Decimal("0.05"),
}


# ── Result containers ─────────────────────────────────────────────────────────


@dataclass
class ExitStrategyResult:
    """One exit strategy scenario result."""

    hold_years: int
    scenario_name: str
    appreciation_rate: Decimal
    exit: ExitAnalysis


# ── Public API ─────────────────────────────────────────────────────────────────


def model_exit_strategies(
    property: Property,
    hold_periods: list[int] | None = None,
    appreciation_scenarios: Dict[str, Decimal] | None = None,
    annual_rent_growth_pct: Decimal = Decimal("0.03"),
    annual_expense_inflation_pct: Decimal = Decimal("0.02"),
    marginal_tax_rate: Decimal = Decimal("0.24"),
    selling_costs_pct: Decimal = Decimal("0.06"),
) -> List[ExitStrategyResult]:
    """Model exit strategies across hold periods and appreciation scenarios.

    Runs ``project_hold_period`` for each combination of hold period and
    appreciation scenario, collecting the resulting ``ExitAnalysis``.

    Args:
        property: A ``Property`` instance with financial fields populated.
        hold_periods: List of hold years to model (e.g. [3, 5, 7, 10]).
            Defaults to [3, 5, 7, 10, 15].
        appreciation_scenarios: Mapping of scenario name to annual appreciation
            rate (as a fraction). Defaults to pessimistic/conservative/base/
            optimistic presets.
        annual_rent_growth_pct: Annual rent growth as a fraction.
        annual_expense_inflation_pct: Annual expense inflation as a fraction.
        marginal_tax_rate: Investor's marginal tax rate as a fraction [0, 1].
        selling_costs_pct: Selling costs as a fraction of sale price.

    Returns:
        A list of ``ExitStrategyResult`` (one per combination), ordered first
        by hold period ascending, then by scenario order in the input dict.
    """
    periods = hold_periods or DEFAULT_HOLD_PERIODS
    scenarios = appreciation_scenarios or DEFAULT_APPRECIATION_SCENARIOS

    results: List[ExitStrategyResult] = []

    for hold_years in periods:
        for scenario_name, appr_rate in scenarios.items():
            _, exit_analysis = project_hold_period(
                property,
                hold_years=hold_years,
                annual_rent_growth_pct=annual_rent_growth_pct,
                annual_appreciation_pct=appr_rate,
                annual_expense_inflation_pct=annual_expense_inflation_pct,
                marginal_tax_rate=marginal_tax_rate,
                selling_costs_pct=selling_costs_pct,
            )
            results.append(
                ExitStrategyResult(
                    hold_years=hold_years,
                    scenario_name=scenario_name,
                    appreciation_rate=appr_rate,
                    exit=exit_analysis,
                )
            )

    return results


def exit_strategy_table(
    property: Property,
    hold_periods: list[int] | None = None,
    appreciation_scenarios: Dict[str, Decimal] | None = None,
    annual_rent_growth_pct: Decimal = Decimal("0.03"),
    annual_expense_inflation_pct: Decimal = Decimal("0.02"),
    marginal_tax_rate: Decimal = Decimal("0.24"),
    selling_costs_pct: Decimal = Decimal("0.06"),
) -> List[Dict[str, Any]]:
    """Return exit strategy results as a list of flat dict rows.

    Same arguments as :func:`model_exit_strategies`, but each row is a dict
    with the hold period, scenario name, appreciation rate, and the key exit
    metrics (gross sale price, net proceeds after tax, total return,
    annualized IRR).

    Returns:
        A list of dicts with keys: hold_years, scenario_name,
        appreciation_rate, gross_sale_price, selling_costs, loan_payoff,
        net_proceeds_before_tax, estimated_capital_gains_tax,
        net_proceeds_after_tax, total_return, annualized_irr.
    """
    results = model_exit_strategies(
        property,
        hold_periods=hold_periods,
        appreciation_scenarios=appreciation_scenarios,
        annual_rent_growth_pct=annual_rent_growth_pct,
        annual_expense_inflation_pct=annual_expense_inflation_pct,
        marginal_tax_rate=marginal_tax_rate,
        selling_costs_pct=selling_costs_pct,
    )

    rows: List[Dict[str, Any]] = []
    for r in results:
        rows.append(
            {
                "hold_years": r.hold_years,
                "scenario_name": r.scenario_name,
                "appreciation_rate": r.appreciation_rate,
                "gross_sale_price": r.exit.gross_sale_price,
                "selling_costs": r.exit.selling_costs,
                "loan_payoff": r.exit.loan_payoff,
                "net_proceeds_before_tax": r.exit.net_proceeds_before_tax,
                "estimated_capital_gains_tax": r.exit.estimated_capital_gains_tax,
                "net_proceeds_after_tax": r.exit.net_proceeds_after_tax,
                "total_return": r.exit.total_return,
                "annualized_irr": r.exit.annualized_irr,
            }
        )

    return rows
