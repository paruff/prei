from decimal import Decimal

import pytest
from django.urls import reverse

from core.models import InvestmentAnalysis, Property
from core.services.portfolio import compute_portfolio_summary

pytestmark = pytest.mark.django_db


def test_portfolio_summary_total_noi(user, portfolio):
    primary_user_properties = portfolio["primary_user_properties"]
    other_user_property = portfolio["other_user_property"]

    InvestmentAnalysis.objects.create(
        property=primary_user_properties[0],
        noi=Decimal("12000.00"),
        cap_rate=Decimal("0.0369"),
        cash_on_cash=Decimal("0.0600"),
        irr=Decimal("0.0900"),
        dscr=Decimal("1.2000"),
    )
    InvestmentAnalysis.objects.create(
        property=primary_user_properties[1],
        noi=Decimal("18000.00"),
        cap_rate=Decimal("0.0439"),
        cash_on_cash=Decimal("0.0700"),
        irr=Decimal("0.1000"),
        dscr=Decimal("1.2500"),
    )
    InvestmentAnalysis.objects.create(
        property=primary_user_properties[2],
        noi=Decimal("6000.00"),
        cap_rate=Decimal("0.0462"),
        cash_on_cash=Decimal("0.0400"),
        irr=Decimal("0.0800"),
        dscr=Decimal("1.1000"),
    )
    InvestmentAnalysis.objects.create(
        property=other_user_property,
        noi=Decimal("50000.00"),
        cap_rate=Decimal("0.1695"),
        cash_on_cash=Decimal("0.1800"),
        irr=Decimal("0.2100"),
        dscr=Decimal("1.6000"),
    )

    summary = compute_portfolio_summary(user)

    assert summary["total_annual_noi"] == Decimal("36000.00")


def test_portfolio_summary_weighted_cap_rate(user):
    property_one = Property.objects.create(
        user=user,
        address="100 Main St",
        city="Austin",
        state="TX",
        zip_code="78701",
        purchase_price=Decimal("100000.00"),
    )
    property_two = Property.objects.create(
        user=user,
        address="200 Main St",
        city="Austin",
        state="TX",
        zip_code="78702",
        purchase_price=Decimal("300000.00"),
    )
    InvestmentAnalysis.objects.create(
        property=property_one,
        noi=Decimal("10000.00"),
        cap_rate=Decimal("0.9999"),
        cash_on_cash=Decimal("0.0800"),
        irr=Decimal("0.1000"),
        dscr=Decimal("1.3000"),
    )
    InvestmentAnalysis.objects.create(
        property=property_two,
        noi=Decimal("12000.00"),
        cap_rate=Decimal("0.0001"),
        cash_on_cash=Decimal("0.0500"),
        irr=Decimal("0.0800"),
        dscr=Decimal("1.2000"),
    )

    summary = compute_portfolio_summary(user)
    expected_weighted_cap_rate = Decimal("22000.00") / Decimal("400000.00")

    assert summary["weighted_average_cap_rate"] == expected_weighted_cap_rate


def test_portfolio_summary_empty_portfolio(user):
    summary = compute_portfolio_summary(user)

    assert summary == {
        "total_properties": 0,
        "total_capital_invested": Decimal("0"),
        "total_annual_noi": Decimal("0"),
        "weighted_average_cap_rate": Decimal("0"),
        "total_monthly_cash_flow": Decimal("0"),
    }


def test_dashboard_shows_portfolio_summary(client, user):
    property_obj = Property.objects.create(
        user=user,
        address="11 Market St",
        city="Dallas",
        state="TX",
        zip_code="75001",
        purchase_price=Decimal("200000.00"),
    )
    InvestmentAnalysis.objects.create(
        property=property_obj,
        noi=Decimal("12000.00"),
        cap_rate=Decimal("0.0600"),
        cash_on_cash=Decimal("0.0700"),
        irr=Decimal("0.0900"),
        dscr=Decimal("1.3000"),
    )

    client.force_login(user)
    response = client.get(reverse("dashboard"))

    assert response.status_code == 200
    assert response.context["portfolio_summary"]["total_annual_noi"] == Decimal(
        "12000.00"
    )
    assert response.context["portfolio_summary"][
        "weighted_average_cap_rate"
    ] == Decimal("0.06")
    content = response.content.decode()
    assert "Total Annual NOI" in content
    assert "Weighted Average Cap Rate" in content
    assert "portfolio-allocation-chart" in content
