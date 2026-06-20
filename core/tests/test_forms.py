from decimal import Decimal

import pytest
from django.urls import reverse

from core.forms import OperatingExpenseForm, PropertyForm, RentalIncomeForm
from core.models import OperatingExpense, Property, RentalIncome


@pytest.mark.django_db
def test_property_form_includes_expected_fields():
    form = PropertyForm()
    # The form includes location, property details, purchase, income, expenses, loan, and assumption fields
    expected_fields = [
        "address",
        "city",
        "state",
        "zip_code",
        "property_type",
        "bedrooms",
        "bathrooms",
        "square_footage",
        "num_units",
        "year_built",
        "purchase_price",
        "purchase_date",
        "monthly_rent_gross",
        "other_monthly_income",
        "property_taxes_annual",
        "insurance_annual",
        "hoa_monthly",
        "down_payment_pct",
        "interest_rate",
        "loan_term_years",
        "vacancy_rate",
        "mgmt_fee_pct",
        "maintenance_monthly",
        "capex_monthly",
    ]
    assert list(form.fields.keys()) == expected_fields


@pytest.mark.django_db
def test_property_form_maps_square_footage_and_units(user):
    form = PropertyForm(
        data={
            "address": "123 Main St",
            "city": "Austin",
            "state": "TX",
            "zip_code": "78701",
            "purchase_price": "250000.00",
            "purchase_date": "2025-01-01",
            "property_type": "SFR",
            "square_footage": "1500",
            "num_units": "2",
            "year_built": "1995",
            "monthly_rent_gross": "1500.00",
            "other_monthly_income": "0.00",
            "property_taxes_annual": "3000.00",
            "insurance_annual": "1200.00",
            "hoa_monthly": "0.00",
            "down_payment_pct": "0.20",
            "interest_rate": "0.07",
            "loan_term_years": "30",
            "vacancy_rate": "0.08",
            "mgmt_fee_pct": "0.10",
            "maintenance_monthly": "150.00",
            "capex_monthly": "100.00",
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
            "property_type": "SFR",
            "square_footage": "1800",
            "num_units": "1",
            "year_built": "2001",
            "monthly_rent_gross": "2000.00",
            "other_monthly_income": "0.00",
            "property_taxes_annual": "4000.00",
            "insurance_annual": "1500.00",
            "hoa_monthly": "0.00",
            "down_payment_pct": "0.20",
            "interest_rate": "0.07",
            "loan_term_years": "30",
            "vacancy_rate": "0.08",
            "mgmt_fee_pct": "0.10",
            "maintenance_monthly": "150.00",
            "capex_monthly": "100.00",
        },
    )
    assert add_property_response.status_code == 302
    created_property = Property.objects.get(address="44 Workflow Ln")
    assert add_property_response.url == reverse(
        "property_detail", kwargs={"pk": created_property.pk}
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
def test_property_workflow_views_require_login(client):
    response = client.get(reverse("property_add"))
    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


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

    other_user_client = client.__class__()
    other_user_client.force_login(second_user)
    forbidden_response = other_user_client.get(
        reverse("property_edit", kwargs={"pk": property_obj.pk})
    )
    assert forbidden_response.status_code == 404

    delete_confirm = client.get(
        reverse("property_edit", kwargs={"pk": property_obj.pk})
    )
    assert delete_confirm.status_code == 200
    assert "Save changes" in delete_confirm.content.decode()

    delete_get = client.get(reverse("property_delete", kwargs={"pk": property_obj.pk}))
    assert delete_get.status_code == 405

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
