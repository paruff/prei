"""
Example Django models for properties and investment analysis.

These are seed models to get started — feel free to extend with relations,
validation, and business rules as the domain requires.
"""

from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class Property(models.Model):
    """
    A real estate asset.
    """

    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, blank=True)
    purchase_price = models.DecimalField(
        max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    purchase_date = models.DateField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.name} — {self.city}, {self.state}"


class RentalIncome(models.Model):
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="rental_incomes"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()

    def __str__(self) -> str:
        return f"{self.property} income {self.amount} on {self.date}"


class OperatingExpense(models.Model):
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="operating_expenses"
    )
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()

    def __str__(self) -> str:
        return f"{self.property} expense {self.category} {self.amount}"


class Transaction(models.Model):
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="transactions"
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date = models.DateField()

    def __str__(self) -> str:
        return f"{self.description} ({self.amount})"


class InvestmentAnalysis(models.Model):
    """
    A snapshot of calculated KPIs for a property at a point in time.
    Store inputs so results are auditable.
    """

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="analyses"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    # Cached KPI values for quick access (recompute if inputs change)
    noi = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    cap_rate = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True
    )
    cash_on_cash = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True
    )
    irr = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)

    def __str__(self) -> str:
        return f"Analysis for {self.property} at {self.created_at}"
