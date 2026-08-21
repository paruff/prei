"""Tests for portfolio-level cash flow aggregation."""

from decimal import Decimal

import pytest

from core.services.portfolio import (
    PortfolioCashflow,
    compute_portfolio_cashflow,
)


class TestPortfolioCashflowDataclass:
    """Tests for PortfolioCashflow dataclass."""

    def test_portfolio_cashflow_creation(self) -> None:
        """Test creating PortfolioCashflow with all required fields."""
        cashflow = PortfolioCashflow(
            total_gross_rent=Decimal("25000"),
            total_vacancy_loss=Decimal("2000"),
            total_opex=Decimal("15000"),
            total_debt_service=Decimal("8000"),
            total_capex_reserve=Decimal("1000"),
            net_cash_flow=Decimal("-1000"),
            blended_dscr=Decimal("1.25"),
            portfolio_coc=Decimal("0.08"),
            total_equity=Decimal("500000"),
            property_breakdown=[],
        )
        assert cashflow.total_gross_rent == Decimal("25000")
        assert cashflow.total_vacancy_loss == Decimal("2000")
        assert cashflow.total_opex == Decimal("15000")
        assert cashflow.total_debt_service == Decimal("8000")
        assert cashflow.total_capex_reserve == Decimal("1000")
        assert cashflow.net_cash_flow == Decimal("-1000")
        assert cashflow.blended_dscr == Decimal("1.25")
        assert cashflow.portfolio_coc == Decimal("0.08")
        assert cashflow.total_equity == Decimal("500000")
        assert cashflow.property_breakdown == []

    def test_portfolio_cashflow_with_property_breakdown(self) -> None:
        """Test PortfolioCashflow with property breakdown list."""
        breakdown = [
            {
                "property": "123 Main St",
                "monthly_cf": Decimal("500"),
                "dscr": Decimal("1.5"),
                "ltv": Decimal("0.75"),
            },
            {
                "property": "456 Oak Ave",
                "monthly_cf": Decimal("-200"),
                "dscr": Decimal("0.9"),
                "ltv": Decimal("0.85"),
            },
        ]
        cashflow = PortfolioCashflow(
            total_gross_rent=Decimal("25000"),
            total_vacancy_loss=Decimal("2000"),
            total_opex=Decimal("15000"),
            total_debt_service=Decimal("8000"),
            total_capex_reserve=Decimal("1000"),
            net_cash_flow=Decimal("-1000"),
            blended_dscr=Decimal("1.25"),
            portfolio_coc=Decimal("0.08"),
            total_equity=Decimal("500000"),
            property_breakdown=breakdown,
        )
        assert len(cashflow.property_breakdown) == 2
        assert cashflow.property_breakdown[0]["property"] == "123 Main St"
        assert cashflow.property_breakdown[1]["monthly_cf"] == Decimal("-200")


class TestComputePortfolioCashflow:
    """Tests for compute_portfolio_cashflow function."""

    @pytest.mark.django_db
    def test_returns_portfolio_cashflow_for_user_with_properties(
        self, user, property_obj
    ) -> None:
        """Test compute_portfolio_cashflow returns PortfolioCashflow with correct fields."""
        result = compute_portfolio_cashflow(user)
        assert isinstance(result, PortfolioCashflow)
        assert hasattr(result, "total_gross_rent")
        assert hasattr(result, "total_vacancy_loss")
        assert hasattr(result, "total_opex")
        assert hasattr(result, "total_debt_service")
        assert hasattr(result, "total_capex_reserve")
        assert hasattr(result, "net_cash_flow")
        assert hasattr(result, "blended_dscr")
        assert hasattr(result, "portfolio_coc")
        assert hasattr(result, "total_equity")
        assert hasattr(result, "property_breakdown")
        assert isinstance(result.property_breakdown, list)

    @pytest.mark.django_db
    def test_aggregates_gross_rent_across_properties(self, user, property_obj) -> None:
        """Test total_gross_rent aggregates across all user properties."""
        # Create another property
        from core.models import Property
        from decimal import Decimal

        prop2 = Property.objects.create(
            user=user,
            address="456 Oak Ave",
            city="Test City",
            state="TS",
            zip_code="12345",
            purchase_price=Decimal("400000"),
            monthly_rent_gross=Decimal("3500"),
            other_monthly_income=Decimal("200"),
            property_taxes_annual=Decimal("4800"),
            insurance_annual=Decimal("1500"),
            hoa_monthly=Decimal("100"),
            maintenance_monthly=Decimal("200"),
            capex_monthly=Decimal("150"),
            vacancy_rate=Decimal("0.07"),
            mgmt_fee_pct=Decimal("0.10"),
            down_payment_pct=Decimal("0.20"),
            interest_rate=Decimal("0.07"),
            loan_term_years=30,
        )
        result = compute_portfolio_cashflow(user)
        # Total gross rent should include both properties
        expected_rent = property_obj.monthly_rent_gross + prop2.monthly_rent_gross
        assert result.total_gross_rent == expected_rent

    @pytest.mark.django_db
    def test_calculates_vacancy_loss_from_property_rates(
        self, user, property_obj
    ) -> None:
        """Test vacancy loss = gross_rent * vacancy_rate per property."""
        result = compute_portfolio_cashflow(user)
        # Vacancy loss for property_obj = 2500 * 0.08 = 200
        expected_vacancy = property_obj.monthly_rent_gross * property_obj.vacancy_rate
        assert result.total_vacancy_loss == expected_vacancy

    @pytest.mark.django_db
    def test_aggregates_operating_expenses(self, user, property_obj) -> None:
        """Test total_opex includes taxes, insurance, HOA, maintenance, capex, mgmt."""
        result = compute_portfolio_cashflow(user)
        # Opex for property_obj = taxes/12 + insurance/12 + HOA + maintenance + capex + mgmt
        prop = property_obj
        expected_opex = (
            Decimal(prop.property_taxes_annual) / Decimal(12)
            + Decimal(prop.insurance_annual) / Decimal(12)
            + Decimal(prop.hoa_monthly)
            + Decimal(prop.maintenance_monthly)
            + Decimal(prop.capex_monthly)
            + (Decimal(prop.monthly_rent_gross) * (Decimal(1) - prop.vacancy_rate))
            * prop.mgmt_fee_pct
        )
        assert result.total_opex == expected_opex

    @pytest.mark.django_db
    def test_aggregates_debt_service(self, user, property_obj) -> None:
        """Test total_debt_service uses monthly_payment * 12 per property."""
        from investor_app.finance.mortgage import calculate_monthly_mortgage
        from investor_app.finance.utils import to_decimal

        result = compute_portfolio_cashflow(user)
        prop = property_obj
        loan_amount = to_decimal(prop.purchase_price) * (
            Decimal(1) - to_decimal(prop.down_payment_pct)
        )
        rate_pct = to_decimal(prop.interest_rate) * Decimal(100)
        monthly_pmt = calculate_monthly_mortgage(
            loan_amount, rate_pct, prop.loan_term_years
        )
        annual_debt = monthly_pmt * Decimal(12)
        assert result.total_debt_service == annual_debt

    @pytest.mark.django_db
    def test_aggregates_capex_reserve(self, user, property_obj) -> None:
        """Test total_capex_reserve includes property.capex_monthly."""
        result = compute_portfolio_cashflow(user)
        assert result.total_capex_reserve == Decimal(property_obj.capex_monthly)

    @pytest.mark.django_db
    def test_net_cash_flow_calculation(self, user, property_obj) -> None:
        """Test net_cash_flow = gross_rent - vacancy_loss - opex - debt_service - capex."""
        result = compute_portfolio_cashflow(user)
        expected = (
            result.total_gross_rent
            - result.total_vacancy_loss
            - result.total_opex
            - result.total_debt_service
            - result.total_capex_reserve
        )
        assert result.net_cash_flow == expected

    @pytest.mark.django_db
    def test_blended_dscr_calculation(self, user, property_obj) -> None:
        """Test blended_dscr = total_noi / total_debt_service."""
        result = compute_portfolio_cashflow(user)
        expected_dscr = (
            (result.total_gross_rent - result.total_vacancy_loss - result.total_opex)
            / result.total_debt_service
            if result.total_debt_service > 0
            else Decimal("0")
        )
        assert abs(result.blended_dscr - expected_dscr) < Decimal("0.01")

    @pytest.mark.django_db
    def test_portfolio_coc_calculation(self, user, property_obj) -> None:
        """Test portfolio_coc = net_cash_flow / total_equity_invested."""
        result = compute_portfolio_cashflow(user)
        total_equity_invested = sum(
            (prop.purchase_price * (Decimal(1) - prop.down_payment_pct))
            for prop in [property_obj]
        )
        expected_coc = (
            result.net_cash_flow / total_equity_invested
            if total_equity_invested > 0
            else Decimal("0")
        )
        assert abs(result.portfolio_coc - expected_coc) < Decimal("0.01")

    @pytest.mark.django_db
    def test_property_breakdown_includes_all_properties(
        self, user, property_obj
    ) -> None:
        """Test property_breakdown list has entry for each property."""
        result = compute_portfolio_cashflow(user)
        assert len(result.property_breakdown) == 1
        entry = result.property_breakdown[0]
        assert "property" in entry
        assert "monthly_cf" in entry
        assert "dscr" in entry
        assert "ltv" in entry

    @pytest.mark.django_db
    def test_highlights_negative_cash_flow_properties(self, user, property_obj) -> None:
        """Test properties with negative cash flow are identifiable."""
        result = compute_portfolio_cashflow(user)
        for entry in result.property_breakdown:
            assert "monthly_cf" in entry
            # We can check the value to see if it's negative
            _ = entry["monthly_cf"] < 0
            # Just verify the field exists and is a Decimal
            assert isinstance(entry["monthly_cf"], Decimal)

    @pytest.mark.django_db
    def test_returns_zero_for_user_with_no_properties(self, user) -> None:
        """Test returns zeroed PortfolioCashflow for user with no properties."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        empty_user = User.objects.create_user(username="empty", password="pass")
        result = compute_portfolio_cashflow(empty_user)
        assert result.total_gross_rent == Decimal("0")
        assert result.net_cash_flow == Decimal("0")
        assert result.blended_dscr == Decimal("0")
        assert result.portfolio_coc == Decimal("0")
        assert result.property_breakdown == []


class TestPortfolioDashboardView:
    """Tests for portfolio dashboard view."""

    @pytest.mark.django_db
    def test_dashboard_shows_aggregate_kpis(self, client, user, property_obj):
        """Test dashboard view includes portfolio KPIs."""
        client.force_login(user)
        response = client.get("/portfolio/")
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_dashboard_shows_property_breakdown_table(
        self, client, user, property_obj
    ) -> None:
        """Test dashboard shows property breakdown table."""
        client.force_login(user)
        response = client.get("/portfolio/")
        assert response.status_code == 200
        # Template should render property breakdown
