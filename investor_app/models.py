"""Django models for real estate investment analysis."""

from django.db import models


class Property(models.Model):
    """Model representing a real estate property."""

    name = models.CharField(max_length=255)
    address = models.TextField()
    purchase_price = models.DecimalField(max_digits=15, decimal_places=2)
    current_value = models.DecimalField(max_digits=15, decimal_places=2)
    square_footage = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    year_built = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for Property model."""

        verbose_name_plural = "properties"

    def __str__(self) -> str:
        """Return string representation of the property."""
        return str(self.name)


class RentalIncome(models.Model):
    """Model representing rental income for a property."""

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="rental_incomes"
    )
    description = models.CharField(max_length=255)
    monthly_amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        """Return string representation of the rental income."""
        return f"{self.description} - ${self.monthly_amount}/mo"


class OperatingExpense(models.Model):
    """Model representing operating expenses for a property."""

    FREQUENCY_CHOICES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("annually", "Annually"),
        ("one_time", "One-time"),
    ]

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="operating_expenses"
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default="monthly"
    )
    category = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        """Return string representation of the operating expense."""
        return f"{self.description} - ${self.amount}"


class InvestmentAnalysis(models.Model):
    """Model representing an investment analysis for a property."""

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="investment_analyses"
    )
    analysis_date = models.DateField()
    noi = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    cap_rate = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True
    )
    cash_on_cash_return = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True
    )
    irr = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True
    )
    total_cash_invested = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for InvestmentAnalysis model."""

        verbose_name_plural = "investment analyses"

    def __str__(self) -> str:
        """Return string representation of the investment analysis."""
        return f"Analysis for {self.property.name} on {self.analysis_date}"
