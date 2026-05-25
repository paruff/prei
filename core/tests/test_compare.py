from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.urls import reverse

from core import views
from core.models import InvestmentAnalysis


@pytest.mark.django_db
def test_compare_two_properties_returns_200(
    client, user, make_property, make_rental_income
):
    property_one = make_property(user=user, address="101 Alpha St")
    property_two = make_property(user=user, address="202 Beta St")
    make_rental_income(property=property_one, monthly_rent=Decimal("2100.00"))
    make_rental_income(property=property_two, monthly_rent=Decimal("2400.00"))
    InvestmentAnalysis.objects.create(
        property=property_one,
        noi=Decimal("12000.00"),
        cap_rate=Decimal("0.0500"),
        cash_on_cash=Decimal("0.0800"),
        irr=Decimal("0.1000"),
        dscr=Decimal("1.2000"),
    )
    InvestmentAnalysis.objects.create(
        property=property_two,
        noi=Decimal("14000.00"),
        cap_rate=Decimal("0.0600"),
        cash_on_cash=Decimal("0.0900"),
        irr=Decimal("0.1100"),
        dscr=Decimal("1.3000"),
    )

    client.force_login(user)
    response = client.get(
        f"{reverse('property_compare')}?ids={property_one.id},{property_two.id}"
    )

    assert response.status_code == 200
    assert any(t.name == "properties/compare.html" for t in response.templates)


@pytest.mark.django_db
def test_compare_highlights_best_cap_rate(
    client, user, make_property, make_rental_income
):
    property_one = make_property(user=user, address="111 Low Cap")
    property_two = make_property(user=user, address="222 High Cap")
    make_rental_income(property=property_one, monthly_rent=Decimal("2000.00"))
    make_rental_income(property=property_two, monthly_rent=Decimal("2200.00"))
    InvestmentAnalysis.objects.create(
        property=property_one,
        noi=Decimal("10000.00"),
        cap_rate=Decimal("0.0500"),
        cash_on_cash=Decimal("0.0700"),
        irr=Decimal("0.0900"),
        dscr=Decimal("1.1000"),
    )
    InvestmentAnalysis.objects.create(
        property=property_two,
        noi=Decimal("12000.00"),
        cap_rate=Decimal("0.0800"),
        cash_on_cash=Decimal("0.1000"),
        irr=Decimal("0.1200"),
        dscr=Decimal("1.3000"),
    )

    client.force_login(user)
    response = client.get(
        f"{reverse('property_compare')}?ids={property_one.id},{property_two.id}"
    )

    content = response.content.decode()
    assert response.status_code == 200
    assert "0.0800" in content
    assert "0.0500" in content
    assert "table-success" in content
    assert "table-danger" in content


@pytest.mark.django_db
def test_compare_rejects_one_property(client, user, make_property):
    property_one = make_property(user=user)
    client.force_login(user)

    response = client.get(f"{reverse('property_compare')}?ids={property_one.id}")

    assert response.status_code == 400
    assert "Select at least 2 properties to compare." in response.content.decode()


@pytest.mark.django_db
def test_compare_excludes_other_users_properties(
    client, user, second_user, make_property, make_rental_income
):
    owned_property = make_property(user=user, address="333 Mine")
    other_users_property = make_property(user=second_user, address="444 Theirs")
    make_rental_income(property=owned_property)
    make_rental_income(property=other_users_property)
    InvestmentAnalysis.objects.create(property=owned_property)
    InvestmentAnalysis.objects.create(property=other_users_property)

    client.force_login(user)
    response = client.get(
        f"{reverse('property_compare')}?ids={owned_property.id},{other_users_property.id}"
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_compare_computes_analysis_when_missing(
    client, user, make_property, make_rental_income, monkeypatch
):
    property_one = make_property(user=user, address="555 Missing Analysis One")
    property_two = make_property(user=user, address="666 Missing Analysis Two")
    make_rental_income(property=property_one)
    make_rental_income(property=property_two)

    call_ids: list[int] = []

    def _fake_compute_analysis_for_property(property_obj):
        call_ids.append(property_obj.id)
        return SimpleNamespace(
            noi=Decimal("10000.00"),
            cap_rate=Decimal("0.0500"),
            cash_on_cash=Decimal("0.0700"),
            irr=Decimal("0.0900"),
            dscr=Decimal("1.1000"),
        )

    monkeypatch.setattr(
        views, "compute_analysis_for_property", _fake_compute_analysis_for_property
    )

    client.force_login(user)
    response = client.get(
        f"{reverse('property_compare')}?ids={property_one.id},{property_two.id}"
    )

    assert response.status_code == 200
    assert sorted(call_ids) == sorted([property_one.id, property_two.id])
    assert "10000.00" in response.content.decode()
