from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from core.models import OperatingExpense, Property, RentalIncome


def test_dashboard_computes_analysis(client, db, user):
    p = Property.objects.create(
        user=user,
        address="123 Main St",
        city="Town",
        state="CA",
        zip_code="90000",
        purchase_price=Decimal("120000"),
    )
    RentalIncome.objects.create(
        property=p,
        monthly_rent=Decimal("2000"),
        effective_date=timezone.now().date(),
        vacancy_rate=Decimal("0.05"),
    )
    OperatingExpense.objects.create(
        property=p,
        category="Tax",
        amount=Decimal("300"),
        frequency=OperatingExpense.Frequency.MONTHLY,
        effective_date=timezone.now().date(),
    )

    url = reverse("dashboard")
    resp = client.get(url)
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "Top Properties" in content
    assert "123 Main St" in content
