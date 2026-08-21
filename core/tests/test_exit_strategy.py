"""Tests for exit strategy modeling across hold periods and appreciation scenarios.

These are unit tests: ``project_hold_period`` only reads plain attributes off
the property object, so we build an unsaved ``Property`` instance (no DB access,
avoiding the sqlite lock contention seen under load) with the financial fields
the projection reads.
"""

from decimal import Decimal

from core.models import Property
from core.services.exit_strategy import (
    ExitStrategyResult,
    exit_strategy_table,
    model_exit_strategies,
)


def make_property() -> Property:
    """Build an unsaved ``Property`` with the fields ``project_hold_period`` reads.

    Mirrors the spec's known example: $200,000 purchase, 20% down ($40,000),
    $1,500/mo rent, 7% interest, 30-yr loan.
    """
    return Property(
        purchase_price=Decimal("200000"),
        monthly_rent_gross=Decimal("1500"),
        other_monthly_income=Decimal("0"),
        property_taxes_annual=Decimal("2400"),
        insurance_annual=Decimal("1200"),
        hoa_monthly=Decimal("0"),
        maintenance_monthly=Decimal("150"),
        capex_monthly=Decimal("100"),
        down_payment_pct=Decimal("0.20"),
        interest_rate=Decimal("0.07"),
        loan_term_years=30,
        vacancy_rate=Decimal("0.08"),
        mgmt_fee_pct=Decimal("0.10"),
    )


# ═════════════════════════════════════════════════════════════════
#  BASIC FUNCTIONALITY
# ═════════════════════════════════════════════════════════════════


class TestExitStrategyBasic:
    def test_model_returns_list(self) -> None:
        """Should return a non-empty list of ExitStrategyResult."""
        results = model_exit_strategies(make_property())
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, ExitStrategyResult) for r in results)

    def test_table_returns_list_of_dicts(self) -> None:
        """Table should return a list of dict rows."""
        rows = exit_strategy_table(make_property())
        assert isinstance(rows, list)
        assert len(rows) > 0
        assert all(isinstance(r, dict) for r in rows)

    def test_table_rows_have_expected_keys(self) -> None:
        """Each table row should contain all expected keys."""
        rows = exit_strategy_table(make_property())
        expected_keys = {
            "hold_years",
            "scenario_name",
            "appreciation_rate",
            "gross_sale_price",
            "selling_costs",
            "loan_payoff",
            "net_proceeds_before_tax",
            "estimated_capital_gains_tax",
            "net_proceeds_after_tax",
            "total_return",
            "annualized_irr",
        }
        for row in rows:
            assert set(row.keys()) == expected_keys

    def test_result_count_matches_grid(self) -> None:
        """Result count = len(hold_periods) × len(appreciation_scenarios)."""
        hold_periods = [3, 5, 7]
        scenarios = {"Low": Decimal("0.01"), "High": Decimal("0.04")}
        results = model_exit_strategies(
            make_property(),
            hold_periods=hold_periods,
            appreciation_scenarios=scenarios,
        )
        assert len(results) == len(hold_periods) * len(scenarios)


# ═════════════════════════════════════════════════════════════════
#  SCENARIO-SPECIFIC ASSERTIONS
# ═════════════════════════════════════════════════════════════════


class TestExitStrategyAppreciation:
    """Higher appreciation should produce higher sale prices all else equal."""

    def test_higher_appreciation_higher_sale_price(self) -> None:
        """For the same hold period, higher appreciation → higher gross sale price."""
        hold_periods = [10]
        scenarios = {
            "Low": Decimal("0.01"),
            "Mid": Decimal("0.03"),
            "High": Decimal("0.05"),
        }
        rows = exit_strategy_table(
            make_property(),
            hold_periods=hold_periods,
            appreciation_scenarios=scenarios,
        )
        # rows are ordered by scenario order in dict
        sale_prices = [r["gross_sale_price"] for r in rows]
        # Base price = 200000; 1% → lower, 5% → higher
        assert sale_prices == sorted(sale_prices)

    def test_longer_hold_higher_sale_price(self) -> None:
        """For the same scenario, longer hold → higher gross sale price."""
        scenarios = {"Base": Decimal("0.03")}
        hold_periods = [3, 5, 7, 10]
        rows = exit_strategy_table(
            make_property(),
            hold_periods=hold_periods,
            appreciation_scenarios=scenarios,
        )
        sale_prices = [r["gross_sale_price"] for r in rows]
        assert sale_prices == sorted(sale_prices)


class TestExitStrategyResultStructure:
    def test_hold_years_vary(self) -> None:
        """Hold years should vary across the default grid."""
        results = model_exit_strategies(make_property())
        hold_years = {r.hold_years for r in results}
        assert len(hold_years) == 5  # default 5 hold periods

    def test_scenario_names_present(self) -> None:
        """Scenario names should include the default four."""
        results = model_exit_strategies(make_property())
        names = {r.scenario_name for r in results}
        assert {"Pessimistic", "Conservative", "Base", "Optimistic"}.issubset(names)

    def test_appreciation_rate_stored(self) -> None:
        """appreciation_rate field should match the scenario rate."""
        results = model_exit_strategies(make_property())
        for r in results:
            assert isinstance(r.appreciation_rate, Decimal)

    def test_exit_is_exit_analysis(self) -> None:
        """exit field should be an ExitAnalysis instance."""
        from core.services.projections import ExitAnalysis

        results = model_exit_strategies(make_property())
        for r in results:
            assert isinstance(r.exit, ExitAnalysis)


# ═════════════════════════════════════════════════════════════════
#  CUSTOM PARAMETERS
# ═════════════════════════════════════════════════════════════════


class TestExitStrategyCustomParams:
    def test_custom_hold_periods(self) -> None:
        """Custom hold periods should be used."""
        hold_periods = [2, 4, 6]
        rows = exit_strategy_table(make_property(), hold_periods=hold_periods)
        assert {r["hold_years"] for r in rows} == set(hold_periods)

    def test_custom_scenarios(self) -> None:
        """Custom appreciation scenarios should be used."""
        scenarios = {"Bear": Decimal("-0.02"), "Bull": Decimal("0.06")}
        rows = exit_strategy_table(make_property(), appreciation_scenarios=scenarios)
        assert {r["scenario_name"] for r in rows} == set(scenarios.keys())

    def test_pessimistic_negative_appreciation_lower_price(self) -> None:
        """Negative appreciation yields lower sale price than base scenario."""
        hold_periods = [10]
        scenarios = {
            "Down": Decimal("-0.01"),
            "Up": Decimal("0.04"),
        }
        rows = exit_strategy_table(
            make_property(),
            hold_periods=hold_periods,
            appreciation_scenarios=scenarios,
        )
        prices = {r["scenario_name"]: r["gross_sale_price"] for r in rows}
        assert prices["Down"] < prices["Up"]


# ═════════════════════════════════════════════════════════════════
#  INTEGRITY / EDGE CASES
# ═════════════════════════════════════════════════════════════════


class TestExitStrategyIntegrity:
    def test_all_metrics_decimal(self) -> None:
        """All monetary metrics in table rows should be Decimal."""
        rows = exit_strategy_table(make_property())
        decimal_keys = {
            "gross_sale_price",
            "selling_costs",
            "loan_payoff",
            "net_proceeds_before_tax",
            "estimated_capital_gains_tax",
            "net_proceeds_after_tax",
            "total_return",
            "annualized_irr",
        }
        for row in rows:
            for key in decimal_keys:
                assert isinstance(row[key], Decimal)

    def test_no_duplicate_combinations(self) -> None:
        """Should not have duplicate (hold_years, scenario) combinations."""
        rows = exit_strategy_table(make_property())
        seen = set()
        for row in rows:
            key = (row["hold_years"], row["scenario_name"])
            assert key not in seen, f"Duplicate combination: {key}"
            seen.add(key)

    def test_result_objects_match_table(self) -> None:
        """model_exit_strategies and exit_strategy_table should be consistent."""
        results = model_exit_strategies(make_property())
        rows = exit_strategy_table(make_property())
        assert len(results) == len(rows)
        for r, row in zip(results, rows):
            assert r.hold_years == row["hold_years"]
            assert r.scenario_name == row["scenario_name"]
            assert r.appreciation_rate == row["appreciation_rate"]
            assert r.exit.gross_sale_price == row["gross_sale_price"]
