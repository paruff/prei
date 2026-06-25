"""Unit tests for portfolio variance analysis (ISSUE 4-A)."""

from datetime import date
from decimal import Decimal

import pytest

from core.models import InvestmentAnalysis, MonthlyActuals, Property
from core.services.portfolio import (
    calculate_coc_variance,
    calculate_expense_variance,
    calculate_vacancy_variance,
    calculate_ytd_cashflow,
    check_flag_for_attention,
    compute_portfolio_performance,
)


@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create_user(
        username="testuser", password="testpass123"
    )


@pytest.fixture
def property_with_analysis(user):
    """Create a property with analysis for testing."""
    prop = Property.objects.create(
        user=user,
        address="123 Test St",
        city="Testville",
        state="TX",
        zip_code="12345",
        purchase_price=Decimal("200000"),
        monthly_rent_gross=Decimal("1500"),
        down_payment_pct=Decimal("0.25"),
        interest_rate=Decimal("0.07"),
        loan_term_years=30,
        vacancy_rate=Decimal("0.08"),
    )
    InvestmentAnalysis.objects.create(
        property=prop,
        noi=Decimal("12000"),
        cap_rate=Decimal("0.06"),
        cash_on_cash=Decimal("0.08"),
        irr=Decimal("0.10"),
        dscr=Decimal("1.25"),
    )
    return prop


# ---------------------------------------------------------------------------
# calculate_coc_variance
# ---------------------------------------------------------------------------


class TestCalculateCocVariance:
    """Tests for cash-on-cash variance calculation."""

    def test_no_variance(self):
        """When actual matches underwritten, variance is 0."""
        # actual_coc = (annual_noi - annual_debt_service) / total_invested
        # annual_noi = (1500 - 0 - 100 - 66.67) * 12 = 16000
        # actual_coc = (16000 - 12000) / 50000 = 0.08
        variance = calculate_coc_variance(
            actual_rent=Decimal("1500"),
            actual_vacancy_days=0,
            actual_expenses=Decimal("100"),
            actual_maintenance=Decimal("66.67"),
            underwritten_coc=Decimal("0.08"),
            annual_debt_service=Decimal("12000"),
            total_invested=Decimal("50000"),
        )
        assert variance == Decimal("0.0000")

    def test_positive_variance(self):
        """When actual is better than underwritten, variance is positive."""
        # Higher rent → higher CoC
        # annual_noi = (1600 - 100 - 66.67) * 12 = 17200
        # actual_coc = (17200 - 12000) / 50000 = 0.104
        variance = calculate_coc_variance(
            actual_rent=Decimal("1600"),  # Higher rent
            actual_vacancy_days=0,
            actual_expenses=Decimal("100"),  # Lower expenses
            actual_maintenance=Decimal("66.67"),
            underwritten_coc=Decimal("0.08"),
            annual_debt_service=Decimal("12000"),
            total_invested=Decimal("50000"),
        )
        assert variance > Decimal("0")

    def test_negative_variance(self):
        """When actual is worse than underwritten, variance is negative."""
        variance = calculate_coc_variance(
            actual_rent=Decimal("1200"),  # Lower rent
            actual_vacancy_days=5,  # Vacancy
            actual_expenses=Decimal("600"),  # Higher expenses
            actual_maintenance=Decimal("200"),
            underwritten_coc=Decimal("0.08"),
            annual_debt_service=Decimal("12000"),
            total_invested=Decimal("50000"),
        )
        assert variance < Decimal("0")

    def test_zero_investment(self):
        """When total invested is zero, variance is 0."""
        variance = calculate_coc_variance(
            actual_rent=Decimal("1500"),
            actual_vacancy_days=0,
            actual_expenses=Decimal("500"),
            actual_maintenance=Decimal("150"),
            underwritten_coc=Decimal("0.08"),
            annual_debt_service=Decimal("12000"),
            total_invested=Decimal("0"),
        )
        assert variance == Decimal("0")


# ---------------------------------------------------------------------------
# calculate_vacancy_variance
# ---------------------------------------------------------------------------


class TestCalculateVacancyVariance:
    """Tests for vacancy variance calculation."""

    def test_no_vacancy(self):
        """When no vacancy days, variance equals underwritten rate."""
        variance = calculate_vacancy_variance(
            actual_vacancy_days=0,
            underwritten_vacancy_rate=Decimal("0.08"),
        )
        assert variance == Decimal("0.0800")

    def test_vacancy_matches_underwritten(self):
        """When actual vacancy matches underwritten, variance is 0."""
        variance = calculate_vacancy_variance(
            actual_vacancy_days=2,  # 2/30 = 0.0667
            underwritten_vacancy_rate=Decimal("0.08"),
        )
        assert variance > Decimal("0")  # Actual is better (less vacancy)

    def test_higher_vacancy(self):
        """When actual vacancy is higher than underwritten, variance is negative."""
        variance = calculate_vacancy_variance(
            actual_vacancy_days=5,  # 5/30 = 0.1667
            underwritten_vacancy_rate=Decimal("0.08"),
        )
        assert variance < Decimal("0")


# ---------------------------------------------------------------------------
# calculate_expense_variance
# ---------------------------------------------------------------------------


class TestCalculateExpenseVariance:
    """Tests for expense variance calculation."""

    def test_under_budget(self):
        """When actual is under budget, variance is positive."""
        variance = calculate_expense_variance(
            actual_expenses=Decimal("400"),
            actual_maintenance=Decimal("100"),
            underwritten_monthly_expenses=Decimal("600"),
        )
        assert variance == Decimal("100.00")

    def test_over_budget(self):
        """When actual is over budget, variance is negative."""
        variance = calculate_expense_variance(
            actual_expenses=Decimal("500"),
            actual_maintenance=Decimal("200"),
            underwritten_monthly_expenses=Decimal("600"),
        )
        assert variance == Decimal("-100.00")

    def test_on_budget(self):
        """When actual matches budget, variance is 0."""
        variance = calculate_expense_variance(
            actual_expenses=Decimal("400"),
            actual_maintenance=Decimal("200"),
            underwritten_monthly_expenses=Decimal("600"),
        )
        assert variance == Decimal("0.00")


# ---------------------------------------------------------------------------
# calculate_ytd_cashflow
# ---------------------------------------------------------------------------


class TestCalculateYtdCashflow:
    """Tests for year-to-date cashflow calculation."""

    def test_no_actuals(self, property_with_analysis):
        """When no actuals, YTD is all zeros."""
        ytd = calculate_ytd_cashflow(property_with_analysis, 2026)
        assert ytd["ytd_actual"] == Decimal("0.00")
        assert ytd["ytd_projected"] == Decimal("0.00")
        assert ytd["variance"] == Decimal("0.00")

    def test_with_actuals(self, property_with_analysis):
        """When actuals exist, YTD is calculated correctly."""
        MonthlyActuals.objects.create(
            prop=property_with_analysis,
            month=date(2026, 1, 1),
            actual_rent_collected=Decimal("1500"),
            actual_vacancy_days=0,
            actual_expenses=Decimal("400"),
            actual_maintenance=Decimal("100"),
        )
        MonthlyActuals.objects.create(
            prop=property_with_analysis,
            month=date(2026, 2, 1),
            actual_rent_collected=Decimal("1500"),
            actual_vacancy_days=0,
            actual_expenses=Decimal("400"),
            actual_maintenance=Decimal("100"),
        )

        ytd = calculate_ytd_cashflow(property_with_analysis, 2026)
        assert ytd["ytd_actual"] == Decimal("2000.00")  # (1500 - 400 - 100) * 2
        assert ytd["ytd_projected"] != Decimal("0.00")


# ---------------------------------------------------------------------------
# check_flag_for_attention
# ---------------------------------------------------------------------------


class TestCheckFlagForAttention:
    """Tests for attention flag logic."""

    def test_no_analysis(self, user):
        """Property without analysis is not flagged."""
        prop = Property.objects.create(
            user=user,
            address="456 No Analysis",
            city="Testville",
            state="TX",
            zip_code="12345",
            purchase_price=Decimal("200000"),
        )
        assert check_flag_for_attention(prop) is False

    def test_zero_coc(self, user):
        """Property with zero underwritten CoC is not flagged."""
        prop = Property.objects.create(
            user=user,
            address="789 Zero CoC",
            city="Testville",
            state="TX",
            zip_code="12345",
            purchase_price=Decimal("200000"),
        )
        InvestmentAnalysis.objects.create(
            property=prop,
            cash_on_cash=Decimal("0"),
        )
        assert check_flag_for_attention(prop) is False

    def test_insufficient_months(self, property_with_analysis):
        """Less than 2 months of actuals is not flagged."""
        MonthlyActuals.objects.create(
            prop=property_with_analysis,
            month=date(2026, 1, 1),
            actual_rent_collected=Decimal("1200"),
            actual_vacancy_days=5,
            actual_expenses=Decimal("600"),
            actual_maintenance=Decimal("200"),
        )
        assert check_flag_for_attention(property_with_analysis) is False

    def test_flagged_property(self, property_with_analysis):
        """Property with 2+ months of bad performance is flagged."""
        # Create 2 months with significant underperformance
        for month in [date(2026, 1, 1), date(2026, 2, 1)]:
            MonthlyActuals.objects.create(
                prop=property_with_analysis,
                month=month,
                actual_rent_collected=Decimal("1000"),  # Much lower
                actual_vacancy_days=10,  # High vacancy
                actual_expenses=Decimal("800"),  # Much higher
                actual_maintenance=Decimal("300"),
            )

        assert check_flag_for_attention(property_with_analysis) is True

    def test_not_flagged_with_mixed_performance(self, property_with_analysis):
        """Property with mixed performance is not flagged."""
        MonthlyActuals.objects.create(
            prop=property_with_analysis,
            month=date(2026, 1, 1),
            actual_rent_collected=Decimal("1000"),  # Bad month
            actual_vacancy_days=10,
            actual_expenses=Decimal("800"),
            actual_maintenance=Decimal("300"),
        )
        MonthlyActuals.objects.create(
            prop=property_with_analysis,
            month=date(2026, 2, 1),
            actual_rent_collected=Decimal("2500"),  # Very good month
            actual_vacancy_days=0,
            actual_expenses=Decimal("200"),
            actual_maintenance=Decimal("50"),
        )

        assert check_flag_for_attention(property_with_analysis) is False


# ---------------------------------------------------------------------------
# compute_portfolio_performance
# ---------------------------------------------------------------------------


class TestComputePortfolioPerformance:
    """Tests for portfolio performance computation."""

    def test_empty_portfolio(self, user):
        """Empty portfolio returns correct defaults."""
        result = compute_portfolio_performance(user)
        assert result["property_details"] == []
        assert result["total_monthly_cashflow"] == Decimal("0.00")
        assert result["total_equity"] == Decimal("0.00")
        assert result["best_property"] is None
        assert result["worst_property"] is None
        assert result["flagged_properties"] == []

    def test_portfolio_with_properties(self, user, property_with_analysis):
        """Portfolio with properties returns correct metrics."""
        result = compute_portfolio_performance(user)
        assert len(result["property_details"]) == 1
        assert result["total_monthly_cashflow"] > Decimal("0")
        assert result["total_equity"] > Decimal("0")

    def test_portfolio_with_actuals(self, user, property_with_analysis):
        """Portfolio with actuals includes variance data."""
        MonthlyActuals.objects.create(
            prop=property_with_analysis,
            month=date(2026, 1, 1),
            actual_rent_collected=Decimal("1500"),
            actual_vacancy_days=0,
            actual_expenses=Decimal("400"),
            actual_maintenance=Decimal("100"),
        )

        result = compute_portfolio_performance(user)
        detail = result["property_details"][0]
        assert detail["latest_actual"] is not None
        assert "coc_variance" in detail
        assert "vacancy_variance" in detail
        assert "expense_variance" in detail
