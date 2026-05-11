from decimal import Decimal


def test_rental_income_fixture_effective_gross_income(rental_income_sfr):
    assert rental_income_sfr.effective_gross_income() == Decimal("2280.000000")


def test_operating_expense_fixtures_monthly_amounts(
    expense_property_tax_annual,
    expense_maintenance_monthly,
):
    assert expense_property_tax_annual.monthly_amount() == Decimal("325.00")
    assert expense_maintenance_monthly.monthly_amount() == Decimal("200.00")


def test_analysis_with_financing_fixture_has_stress_metrics(analysis_with_financing):
    assert analysis_with_financing.cash_on_cash < Decimal("0")
    assert analysis_with_financing.dscr < Decimal("1.0000")


def test_full_sfr_composite_fixture(full_sfr):
    assert set(full_sfr.keys()) == {"property", "rental_income", "expenses", "analysis"}
    assert len(full_sfr["expenses"]) == 5
    assert full_sfr["analysis"].property == full_sfr["property"]


def test_portfolio_fixture_bundles_expected_properties(portfolio):
    assert len(portfolio["primary_user_properties"]) == 3
    assert portfolio["other_user_property"] not in portfolio["primary_user_properties"]
