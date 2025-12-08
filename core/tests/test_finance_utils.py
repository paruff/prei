from decimal import Decimal

from investor_app.finance.utils import (
    calculate_break_even_rent,
    calculate_carrying_costs,
    calculate_maintenance_reserve,
    calculate_monthly_mortgage,
    calculate_property_tax,
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
        property_value=Decimal("250000"),
        property_type="single-family",
        year_built=2000
    )
    
    # Should be close to base rate for $250k home built in 2000
    assert insurance > Decimal("1000")
    assert insurance < Decimal("2000")


def test_estimate_insurance_condo():
    """Test insurance estimation for condo (should be lower)."""
    sf_insurance = estimate_insurance(
        property_value=Decimal("250000"),
        property_type="single-family",
        year_built=2000
    )
    condo_insurance = estimate_insurance(
        property_value=Decimal("250000"),
        property_type="condo",
        year_built=2000
    )
    
    # Condo should be cheaper (0.7x factor)
    assert condo_insurance < sf_insurance


def test_estimate_insurance_old_property():
    """Test insurance estimation for older property (should be higher)."""
    new_insurance = estimate_insurance(
        property_value=Decimal("250000"),
        property_type="single-family",
        year_built=2020
    )
    old_insurance = estimate_insurance(
        property_value=Decimal("250000"),
        property_type="single-family",
        year_built=1970
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
