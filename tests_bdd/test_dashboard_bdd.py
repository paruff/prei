import pytest
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import Property, RentalIncome, OperatingExpense


@pytest.fixture
def user(db):
    User = get_user_model()
    return User.objects.create_user(
        username="tester", email="tester@example.com", password="pass"
    )


def test_bdd_dashboard_flow(client, db, user):
    # Given a user exists (fixture)
    # And a property exists
    p = Property.objects.create(
        user=user,
        address="123 Main St",
        city="Town",
        state="CA",
        zip_code="90000",
        purchase_price=Decimal("120000"),
    )
    # And rental income exists
    RentalIncome.objects.create(
        property=p,
        monthly_rent=Decimal("2000"),
        effective_date=timezone.now().date(),
        vacancy_rate=Decimal("0.05"),
    )
    # And a monthly operating expense exists
    OperatingExpense.objects.create(
        property=p,
        category="Tax",
        amount=Decimal("300"),
        frequency=OperatingExpense.Frequency.MONTHLY,
        effective_date=timezone.now().date(),
    )
    # When I visit the dashboard
    resp = client.get(reverse("dashboard"))
    # Then I see content
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Top Properties" in html
    assert "123 Main St" in html
