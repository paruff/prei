from decimal import Decimal

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse

from core.admin import PropertyAdmin
from core.models import Property

User = get_user_model()


@pytest.mark.django_db
def test_user_a_cannot_see_user_b_property(client, user, second_user):
    property_b = Property.objects.create(
        user=second_user,
        address="200 Other St",
        city="Austin",
        state="TX",
        zip_code="78702",
        purchase_price=Decimal("310000"),
    )
    client.force_login(user)

    response = client.get(f"/properties/{property_b.id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_user_a_list_does_not_contain_user_b_property(client, user, second_user):
    Property.objects.create(
        user=user,
        address="100 My St",
        city="Austin",
        state="TX",
        zip_code="78701",
        purchase_price=Decimal("300000"),
    )
    Property.objects.create(
        user=second_user,
        address="200 Other St",
        city="Austin",
        state="TX",
        zip_code="78702",
        purchase_price=Decimal("310000"),
    )
    client.force_login(user)

    response = client.get(reverse("dashboard"))
    html = response.content.decode()

    assert response.status_code == 200
    assert "100 My St" in html
    assert "200 Other St" not in html


@pytest.mark.django_db
def test_admin_queryset_filtered_for_non_superuser(user, second_user):
    owned_property = Property.objects.create(
        user=user,
        address="100 My St",
        city="Austin",
        state="TX",
        zip_code="78701",
        purchase_price=Decimal("300000"),
    )
    Property.objects.create(
        user=second_user,
        address="200 Other St",
        city="Austin",
        state="TX",
        zip_code="78702",
        purchase_price=Decimal("310000"),
    )
    request = RequestFactory().get("/admin/core/property/")
    request.user = user
    property_admin = PropertyAdmin(Property, admin.site)

    ids = list(property_admin.get_queryset(request).values_list("id", flat=True))

    assert ids == [owned_property.id]


@pytest.mark.django_db
def test_superuser_sees_all_properties(user, second_user):
    Property.objects.create(
        user=user,
        address="100 My St",
        city="Austin",
        state="TX",
        zip_code="78701",
        purchase_price=Decimal("300000"),
    )
    Property.objects.create(
        user=second_user,
        address="200 Other St",
        city="Austin",
        state="TX",
        zip_code="78702",
        purchase_price=Decimal("310000"),
    )
    superuser = User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="pass1234",
    )
    request = RequestFactory().get("/admin/core/property/")
    request.user = superuser
    property_admin = PropertyAdmin(Property, admin.site)

    assert property_admin.get_queryset(request).count() == 2
