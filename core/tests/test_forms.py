from decimal import Decimal

import pytest
from django.urls import reverse

from core.forms import OperatingExpenseForm, PropertyForm, RentalIncomeForm
from core.models import OperatingExpense, Property, RentalIncome


@pytest.mark.django_db
def test_property_form_includes_expected_fields():
    form = PropertyForm()
    assert list(form.fields.keys()) == [
        "address",
        "city",
        "state",
        "zip_code",
        "purchase_price",
        "purchase_date",
        "property_type",
        "square_footage",
        "num_units",
        "year_built",
    ]


@pytest.mark.django_db
def test_property_form_maps_square_footage_and_units(user):
    form = PropertyForm(
        data={
            "address": "123 Main St",
            "city": "Austin",
            "state": "TX",
            "zip_code": "78701",
            "purchase_price": "250000.00",
            "purchase_date": "2026-01-01",
            "property_type": "single-family",
            "square_footage": "1500",
            "num_units": "2",
            "year_built": "1995",
        }
    )
    assert form.is_valid(), form.errors
    prop = form.save(commit=False)
    prop.user = user
    prop.save()
    assert prop.sqft == 1500
    assert prop.units == 2


@pytest.mark.django_db
def test_rental_income_form_validation():
    form = RentalIncomeForm(data={"monthly_rent": "1800.00"})
    assert not form.is_valid()
    assert "effective_date" in form.errors


@pytest.mark.django_db
def test_operating_expense_form_validation():
    form = OperatingExpenseForm(data={"category": "", "amount": "100.00"})
    assert not form.is_valid()
    assert "category" in form.errors
    assert "frequency" in form.errors
    assert "effective_date" in form.errors


@pytest.mark.django_db
def test_property_workflow_views_create_and_redirect(client, user):
    client.force_login(user)

    add_property_response = client.post(
        reverse("property_add"),
        data={
            "address": "44 Workflow Ln",
            "city": "Austin",
            "state": "TX",
            "zip_code": "78702",
            "purchase_price": "300000.00",
            "purchase_date": "2025-01-01",
            "property_type": "single-family",
            "square_footage": "1800",
            "num_units": "1",
            "year_built": "2001",
        },
    )
    assert add_property_response.status_code == 302
    created_property = Property.objects.get(address="44 Workflow Ln")
    assert add_property_response.url == reverse(
        "property_add_income", kwargs={"pk": created_property.pk}
    )
    assert created_property.analysis is not None

    add_income_response = client.post(
        reverse("property_add_income", kwargs={"pk": created_property.pk}),
        data={
            "monthly_rent": "2200.00",
            "vacancy_rate": "0.0500",
            "effective_date": "2025-01-01",
        },
    )
    assert add_income_response.status_code == 302
    assert add_income_response.url == reverse(
        "property_add_expense", kwargs={"pk": created_property.pk}
    )
    assert RentalIncome.objects.filter(property=created_property).count() == 1

    add_expense_response = client.post(
        reverse("property_add_expense", kwargs={"pk": created_property.pk}),
        data={
            "category": "tax",
            "amount": "300.00",
            "frequency": OperatingExpense.Frequency.MONTHLY,
            "effective_date": "2025-01-01",
            "action": "add_another",
        },
    )
    assert add_expense_response.status_code == 302
    assert add_expense_response.url == reverse(
        "property_add_expense", kwargs={"pk": created_property.pk}
    )
    assert OperatingExpense.objects.filter(property=created_property).count() == 1

    done_response = client.post(
        reverse("property_add_expense", kwargs={"pk": created_property.pk}),
        data={
            "category": "insurance",
            "amount": "120.00",
            "frequency": OperatingExpense.Frequency.MONTHLY,
            "effective_date": "2025-01-02",
            "action": "done",
        },
    )
    assert done_response.status_code == 302
    assert done_response.url == reverse(
        "property_detail", kwargs={"pk": created_property.pk}
    )


@pytest.mark.django_db
def test_property_edit_prepopulated_and_delete_owner_only(client, user, second_user):
    property_obj = Property.objects.create(
        user=user,
        address="12 Edit St",
        city="Austin",
        state="TX",
        zip_code="78701",
        purchase_price=Decimal("310000.00"),
        sqft=1400,
        units=1,
    )
    client.force_login(user)
    edit_response = client.get(reverse("property_edit", kwargs={"pk": property_obj.pk}))
    assert edit_response.status_code == 200
    content = edit_response.content.decode()
    assert "12 Edit St" in content
    assert 'value="1400"' in content

    intruder_client = client.__class__()
    intruder_client.force_login(second_user)
    forbidden_response = intruder_client.get(
        reverse("property_edit", kwargs={"pk": property_obj.pk})
    )
    assert forbidden_response.status_code == 404

    delete_get = client.get(reverse("property_delete", kwargs={"pk": property_obj.pk}))
    assert delete_get.status_code == 200
    assert "Delete property" in delete_get.content.decode()

    delete_post = client.post(
        reverse("property_delete", kwargs={"pk": property_obj.pk})
    )
    assert delete_post.status_code == 302
    assert delete_post.url == reverse("property_list")
    assert not Property.objects.filter(pk=property_obj.pk).exists()


@pytest.mark.django_db
def test_property_add_form_requires_csrf(client, user):
    csrf_client = client.__class__(enforce_csrf_checks=True)
    csrf_client.force_login(user)

    response = csrf_client.post(
        reverse("property_add"),
        data={
            "address": "Missing Token Ave",
            "city": "Austin",
            "state": "TX",
            "zip_code": "78701",
            "purchase_price": "100000.00",
            "num_units": "1",
        },
    )
    assert response.status_code == 403
