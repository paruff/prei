from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models


User = get_user_model()


class Property(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="properties")
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=64)
    zip_code = models.CharField(max_length=16)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2)
    purchase_date = models.DateField(null=True, blank=True)
    sqft = models.IntegerField(null=True, blank=True)
    units = models.IntegerField(default=1)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:  # noqa: D401
        return f"{self.address}, {self.city}, {self.state} {self.zip_code}"


class RentalIncome(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="rental_incomes")
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateField()
    vacancy_rate = models.DecimalField(max_digits=5, decimal_places=4, default=settings.FINANCE_DEFAULTS["vacancy_rate"])  # type: ignore[index]

    def effective_gross_income(self) -> Decimal:
        vr = Decimal(self.vacancy_rate)
        return Decimal(self.monthly_rent) * (Decimal(1) - vr)


class OperatingExpense(models.Model):
    class Frequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        ANNUAL = "annual", "Annual"

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="operating_expenses")
    category = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(max_length=16, choices=Frequency.choices, default=Frequency.MONTHLY)
    effective_date = models.DateField()

    def monthly_amount(self) -> Decimal:
        amt = Decimal(self.amount)
        return amt if self.frequency == self.Frequency.MONTHLY else (amt / Decimal(12))


class Transaction(models.Model):
    class Type(models.TextChoices):
        PURCHASE = "purchase", "Purchase"
        LOAN = "loan", "Loan"
        CAPEX = "capex", "Capex"
        OPEX = "opex", "Opex"

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="transactions")
    type = models.CharField(max_length=16, choices=Type.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    metadata = models.JSONField(default=dict, blank=True)


class InvestmentAnalysis(models.Model):
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name="analysis")
    noi = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    cap_rate = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0"))
    cash_on_cash = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0"))
    irr = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0"))
    dscr = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0"))

    updated_at = models.DateTimeField(auto_now=True)
