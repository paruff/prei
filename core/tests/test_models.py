from decimal import Decimal

from django.utils import timezone

from core.models import Property, RentalIncome, OperatingExpense


def test_rental_income_effective_gross_income(db, user):
    p = Property.objects.create(
        user=user,
        address="123 Main St",
        city="Town",
        state="CA",
        zip_code="90000",
        purchase_price=Decimal("100000"),
    )
    ri = RentalIncome.objects.create(
        property=p,
        monthly_rent=Decimal("2000"),
        effective_date=timezone.now().date(),
        vacancy_rate=Decimal("0.10"),
    )
    assert ri.effective_gross_income() == Decimal("1800")


def test_operating_expense_monthly_amount(db, user):
    p = Property.objects.create(
        user=user,
        address="123 Main St",
        city="Town",
        state="CA",
        zip_code="90000",
        purchase_price=Decimal("100000"),
    )
    oe_m = OperatingExpense.objects.create(
        property=p,
        category="Tax",
        amount=Decimal("300"),
        frequency=OperatingExpense.Frequency.MONTHLY,
        effective_date=timezone.now().date(),
    )
    oe_a = OperatingExpense.objects.create(
        property=p,
        category="Insurance",
        amount=Decimal("1200"),
        frequency=OperatingExpense.Frequency.ANNUAL,
        effective_date=timezone.now().date(),
    )
    assert oe_m.monthly_amount() == Decimal("300")
    assert oe_a.monthly_amount() == Decimal("100")
