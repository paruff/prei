from decimal import Decimal

from investor_app.finance.utils import (
    calculate_appreciation,
    calculate_break_even_rent,
    calculate_carrying_costs,
    calculate_maintenance_reserve,
    calculate_monthly_mortgage,
    calculate_principal_paydown,
    calculate_property_tax,
    calculate_roi_components,
    calculate_tax_benefits,
    cap_rate,
    cash_on_cash,
    dscr,
    estimate_insurance,
    irr,
    noi,
)


def test_noi_basic():
    assert noi(Decimal("1000"), Decimal("300")) == Decimal("8400")


def test_cap_rate_zero_price():
    assert cap_rate(Decimal("12000"), Decimal("0")) == Decimal("0")


def test_cash_on_cash_zero_invested():
    assert cash_on_cash(Decimal("12000"), Decimal("0")) == Decimal("0")


def test_dscr_zero_debt():
    assert dscr(Decimal("12000"), Decimal("0")) == Decimal("0")


def test_irr_simple_positive():
    cf = [Decimal("-100000")] + [Decimal("10000")] * 12
    result = irr(cf)
    assert isinstance(result, Decimal)


def test_calculate_monthly_mortgage_basic():
    """Test mortgage calculation with known values."""
    # $280,000 loan at 7.5% for 30 years should be ~$1958.35
    loan_amount = Decimal("280000")
    interest_rate = Decimal("7.5")
    loan_term_years = 30

    payment = calculate_monthly_mortgage(loan_amount, interest_rate, loan_term_years)

    # Allow small tolerance for rounding
    assert abs(payment - Decimal("1958.35")) < Decimal("1.00")


def test_calculate_monthly_mortgage_zero_interest():
    """Test mortgage calculation with zero interest."""
    loan_amount = Decimal("240000")
    interest_rate = Decimal("0")
    loan_term_years = 30

    payment = calculate_monthly_mortgage(loan_amount, interest_rate, loan_term_years)

    # Should be simple division: 240000 / (30 * 12) = 666.67
    expected = Decimal("666.67")
    assert abs(payment - expected) < Decimal("0.01")


def test_calculate_monthly_mortgage_zero_loan():
    """Test mortgage calculation with zero loan amount."""
    payment = calculate_monthly_mortgage(Decimal("0"), Decimal("7.5"), 30)
    assert payment == Decimal("0")


def test_calculate_property_tax():
    """Test property tax calculation."""
    property_value = Decimal("350000")
    tax_rate = Decimal("2.1")  # 2.1%

    annual_tax = calculate_property_tax(property_value, tax_rate)

    # 350000 * 0.021 = 7350
    assert annual_tax == Decimal("7350.00")


def test_estimate_insurance_single_family():
    """Test insurance estimation for single-family home."""
    insurance = estimate_insurance(
        property_value=Decimal("250000"), property_type="single-family", year_built=2000
    )

    # Should be close to base rate for $250k home built in 2000
    assert insurance > Decimal("1000")
    assert insurance < Decimal("2000")


def test_estimate_insurance_condo():
    """Test insurance estimation for condo (should be lower)."""
    sf_insurance = estimate_insurance(
        property_value=Decimal("250000"), property_type="single-family", year_built=2000
    )
    condo_insurance = estimate_insurance(
        property_value=Decimal("250000"), property_type="condo", year_built=2000
    )

    # Condo should be cheaper (0.7x factor)
    assert condo_insurance < sf_insurance


def test_estimate_insurance_old_property():
    """Test insurance estimation for older property (should be higher)."""
    new_insurance = estimate_insurance(
        property_value=Decimal("250000"), property_type="single-family", year_built=2020
    )
    old_insurance = estimate_insurance(
        property_value=Decimal("250000"), property_type="single-family", year_built=1970
    )

    # Older property should have higher insurance
    assert old_insurance > new_insurance


def test_calculate_maintenance_reserve_basic():
    """Test maintenance reserve calculation (1% rule)."""
    property_value = Decimal("350000")
    maintenance = calculate_maintenance_reserve(property_value, year_built=2000)

    # 1% of 350000 = 3500 with no age adjustment
    assert maintenance == Decimal("3500.00")


def test_calculate_maintenance_reserve_old_property():
    """Test maintenance reserve for old property (should be higher)."""
    property_value = Decimal("350000")
    new_maintenance = calculate_maintenance_reserve(property_value, year_built=2020)
    old_maintenance = calculate_maintenance_reserve(property_value, year_built=1975)

    # Old property should have 1.5x factor
    assert old_maintenance > new_maintenance


def test_calculate_break_even_rent():
    """Test break-even rent calculation."""
    monthly_costs = Decimal("3000")
    vacancy_rate = Decimal("8")  # 8%
    management_fee = Decimal("10")  # 10%

    result = calculate_break_even_rent(monthly_costs, vacancy_rate, management_fee)

    # rent * (1 - 0.08) * (1 - 0.10) = 3000
    # rent * 0.92 * 0.90 = 3000
    # rent = 3000 / 0.828 = 3623.19
    assert "monthly" in result
    assert "annual" in result
    assert abs(result["monthly"] - Decimal("3623.19")) < Decimal("1.00")
    assert abs(result["annual"] - Decimal("43478.26")) < Decimal("20.00")


def test_calculate_carrying_costs_complete():
    """Test complete carrying costs calculation."""
    result = calculate_carrying_costs(
        purchase_price=Decimal("350000"),
        loan_amount=Decimal("280000"),
        interest_rate=Decimal("7.5"),
        loan_term_years=30,
        property_tax_rate=Decimal("2.1"),
        insurance_annual=Decimal("1800"),
        hoa_monthly=Decimal("0"),
        utilities_monthly=Decimal("200"),
        maintenance_annual_percent=Decimal("1.0"),
        property_type="single-family",
        year_built=1995,
    )

    # Verify structure
    assert "monthly" in result
    assert "annual" in result
    assert "mortgage" in result["monthly"]
    assert "propertyTax" in result["monthly"]
    assert "insurance" in result["monthly"]
    assert "total" in result["monthly"]

    # Verify mortgage calculation
    assert abs(result["monthly"]["mortgage"] - Decimal("1958.35")) < Decimal("1.00")

    # Verify property tax: 350000 * 0.021 / 12 = 612.50
    assert abs(result["monthly"]["propertyTax"] - Decimal("612.50")) < Decimal("1.00")

    # Verify insurance: 1800 / 12 = 150
    assert result["monthly"]["insurance"] == Decimal("150.00")

    # Verify total is sum of components
    total = (
        result["monthly"]["mortgage"]
        + result["monthly"]["propertyTax"]
        + result["monthly"]["insurance"]
        + result["monthly"]["hoa"]
        + result["monthly"]["utilities"]
        + result["monthly"]["maintenance"]
    )
    assert result["monthly"]["total"] == total


def test_calculate_carrying_costs_all_cash():
    """Test carrying costs for all-cash purchase (no mortgage)."""
    result = calculate_carrying_costs(
        purchase_price=Decimal("350000"),
        loan_amount=Decimal("0"),  # All cash
        interest_rate=Decimal("0"),
        loan_term_years=30,
        property_tax_rate=Decimal("2.1"),
        insurance_annual=Decimal("1800"),
        hoa_monthly=Decimal("0"),
        utilities_monthly=Decimal("200"),
        maintenance_annual_percent=Decimal("1.0"),
        property_type="single-family",
        year_built=1995,
    )

    # Mortgage should be zero
    assert result["monthly"]["mortgage"] == Decimal("0.00")

    # Other costs should still be calculated
    assert result["monthly"]["propertyTax"] > Decimal("0")
    assert result["monthly"]["insurance"] > Decimal("0")
    assert result["monthly"]["maintenance"] > Decimal("0")


def test_calculate_principal_paydown_year1():
    """Test principal paydown calculation for first year."""
    # $280,000 loan at 7.5% for 30 years
    principal = calculate_principal_paydown(
        loan_amount=Decimal("280000"),
        interest_rate=Decimal("7.5"),
        loan_term_years=30,
        num_years=1,
    )

    # First year should pay down a small amount (mostly interest)
    # At 7.5%, most of the payment is interest in year 1
    # Expected: ~$2,500 - $2,700 for year 1
    assert principal > Decimal("2400")
    assert principal < Decimal("2800")


def test_calculate_principal_paydown_zero_loan():
    """Test principal paydown with zero loan amount."""
    principal = calculate_principal_paydown(
        loan_amount=Decimal("0"),
        interest_rate=Decimal("7.5"),
        loan_term_years=30,
        num_years=1,
    )

    assert principal == Decimal("0")


def test_calculate_principal_paydown_zero_interest():
    """Test principal paydown with zero interest (equal payments)."""
    # $240,000 loan at 0% for 30 years
    principal = calculate_principal_paydown(
        loan_amount=Decimal("240000"),
        interest_rate=Decimal("0"),
        loan_term_years=30,
        num_years=1,
    )

    # With 0% interest, annual principal = 240000 / 30 = 8000
    assert abs(principal - Decimal("8000")) < Decimal("0.01")


def test_calculate_appreciation():
    """Test appreciation calculation."""
    appreciation = calculate_appreciation(
        property_value=Decimal("350000"),
        appreciation_rate=Decimal("3.0"),
        num_years=1,
    )

    # 350000 * 0.03 = 10,500
    assert abs(appreciation - Decimal("10500")) < Decimal("1")


def test_calculate_appreciation_five_years():
    """Test appreciation over 5 years (compound)."""
    appreciation = calculate_appreciation(
        property_value=Decimal("350000"),
        appreciation_rate=Decimal("3.0"),
        num_years=5,
    )

    # 350000 * ((1.03)^5 - 1) = 350000 * 0.159274 = 55,745.90
    assert abs(appreciation - Decimal("55745.90")) < Decimal("10")


def test_calculate_tax_benefits_with_loan():
    """Test tax benefits calculation with mortgage."""
    tax_benefits = calculate_tax_benefits(
        loan_amount=Decimal("280000"),
        interest_rate=Decimal("7.5"),
        loan_term_years=30,
        property_value=Decimal("350000"),
        tax_bracket=Decimal("24"),
        year_num=1,
    )

    # Should include mortgage interest deduction + depreciation
    # Year 1 interest ~$21,000, depreciation ~$10,182
    # Total deductions ~$31,182, tax savings ~$7,483
    assert tax_benefits > Decimal("6000")
    assert tax_benefits < Decimal("10000")


def test_calculate_tax_benefits_all_cash():
    """Test tax benefits for all-cash purchase (depreciation only)."""
    tax_benefits = calculate_tax_benefits(
        loan_amount=Decimal("0"),
        interest_rate=Decimal("0"),
        loan_term_years=30,
        property_value=Decimal("350000"),
        tax_bracket=Decimal("24"),
        year_num=1,
    )

    # Only depreciation: 350000 * 0.80 / 27.5 * 0.24 = $2,443.64
    assert abs(tax_benefits - Decimal("2443.64")) < Decimal("10")


def test_calculate_roi_components():
    """Test comprehensive ROI calculation."""
    roi = calculate_roi_components(
        purchase_price=Decimal("350000"),
        loan_amount=Decimal("280000"),
        interest_rate=Decimal("7.5"),
        loan_term_years=30,
        total_cash_invested=Decimal("81300"),
        annual_cash_flow=Decimal("5000"),
        appreciation_rate=Decimal("3.0"),
        tax_bracket=Decimal("24"),
        num_years=5,
    )

    # Verify structure
    assert "year1" in roi
    assert "year5Projected" in roi
    assert "components" in roi

    # Year 1 should have all components
    assert "roi" in roi["year1"]
    assert "cashFlow" in roi["year1"]
    assert "principalPaydown" in roi["year1"]
    assert "appreciation" in roi["year1"]
    assert "taxBenefits" in roi["year1"]

    # Components should be percentages
    assert roi["components"]["cashFlowReturn"] >= Decimal("0")
    assert roi["components"]["appreciationReturn"] >= Decimal("0")
    assert roi["components"]["equityBuildupReturn"] >= Decimal("0")
    assert roi["components"]["taxBenefitsReturn"] >= Decimal("0")

    # Year 1 ROI should be reasonable
    assert roi["year1"]["roi"] > Decimal("-50")  # Not terribly negative
    assert roi["year1"]["roi"] < Decimal("100")  # Not unrealistic


def test_calculate_roi_components_all_cash():
    """Test ROI calculation for all-cash purchase."""
    roi = calculate_roi_components(
        purchase_price=Decimal("350000"),
        loan_amount=Decimal("0"),
        interest_rate=Decimal("0"),
        loan_term_years=30,
        total_cash_invested=Decimal("350000"),
        annual_cash_flow=Decimal("15000"),
        appreciation_rate=Decimal("3.0"),
        tax_bracket=Decimal("24"),
        num_years=5,
    )

    # No principal paydown for all-cash
    assert roi["year1"]["principalPaydown"] == Decimal("0.00")

    # Should still have cash flow, appreciation, and tax benefits
    assert roi["year1"]["cashFlow"] > Decimal("0")
    assert roi["year1"]["appreciation"] > Decimal("0")
    assert roi["year1"]["taxBenefits"] > Decimal("0")
