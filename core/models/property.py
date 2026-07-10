from __future__ import annotations
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

User = get_user_model()


class Property(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="properties")
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=64)
    zip_code = models.CharField(max_length=16)
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    purchase_date = models.DateField(null=True, blank=True)
    sqft = models.IntegerField(null=True, blank=True)
    units = models.IntegerField(default=1)
    notes = models.TextField(blank=True)

    # --- Phase 0: MVP data-entry fields ---
    PROPERTY_TYPE_CHOICES = [
        ("SFR", "Single-Family Residence"),
        ("duplex", "Duplex"),
        ("triplex", "Triplex"),
        ("fourplex", "Fourplex"),
        ("small_multifamily", "Small Multifamily"),
    ]

    property_type = models.CharField(
        max_length=32,
        choices=PROPERTY_TYPE_CHOICES,
        blank=True,
        default="SFR",
    )
    bedrooms = models.PositiveIntegerField(null=True, blank=True)
    bathrooms = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    # Income
    monthly_rent_gross = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    other_monthly_income = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )

    # Expenses (annual / monthly)
    property_taxes_annual = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    insurance_annual = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    hoa_monthly = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )

    # Loan terms
    down_payment_pct = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.20"),
        help_text="Fraction (e.g. 0.20 for 20%)",
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.07"),
        help_text="Annual rate as fraction (e.g. 0.07 for 7%)",
    )
    loan_term_years = models.PositiveIntegerField(default=30)

    # Assumptions (defaults per issue spec)
    vacancy_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.08"),
        help_text="Fraction (e.g. 0.08 for 8%)",
    )
    mgmt_fee_pct = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.10"),
        help_text="Fraction (e.g. 0.10 for 10%)",
    )
    maintenance_monthly = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("150.00")
    )
    capex_monthly = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("100.00")
    )

    def __str__(self) -> str:  # noqa: D401
        return f"{self.address}, {self.city}, {self.state} {self.zip_code}"


class RentalIncome(models.Model):
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="rental_incomes"
    )
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateField()
    vacancy_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=settings.FINANCE_DEFAULTS["vacancy_rate"],
    )  # type: ignore[index]

    def effective_gross_income(self) -> Decimal:
        vr = Decimal(self.vacancy_rate)
        return Decimal(self.monthly_rent) * (Decimal(1) - vr)


class OperatingExpense(models.Model):
    class Frequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        ANNUAL = "annual", "Annual"

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="operating_expenses"
    )
    category = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(
        max_length=16, choices=Frequency.choices, default=Frequency.MONTHLY
    )
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

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="transactions"
    )
    type = models.CharField(max_length=16, choices=Type.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    metadata = models.JSONField(default=dict, blank=True)


class InvestmentAnalysis(models.Model):
    property = models.OneToOneField(
        Property, on_delete=models.CASCADE, related_name="analysis"
    )
    noi = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    cap_rate = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0"))
    cash_on_cash = models.DecimalField(
        max_digits=6, decimal_places=4, default=Decimal("0")
    )
    irr = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0"))
    dscr = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0"))
    hold_years = models.IntegerField(default=5)
    exit_cap_rate = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal("0.06")
    )

    updated_at = models.DateTimeField(auto_now=True)


class MonthlyActuals(models.Model):
    """Monthly actual income and expense figures entered from PM reports.

    Used for variance analysis comparing actuals to underwritten projections.
    """

    prop = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="monthly_actuals"
    )
    month = models.DateField(
        help_text="First day of month, e.g. 2026-06-01",
    )
    actual_rent_collected = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    actual_vacancy_days = models.PositiveIntegerField(
        default=0,
        help_text="Number of vacant days in the month",
    )
    actual_expenses = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Total operating expenses (taxes, insurance, HOA, etc.)",
    )
    actual_maintenance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Maintenance and repair costs",
    )
    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("prop", "month")
        ordering = ["-month"]

    def __str__(self) -> str:  # noqa: D401
        return f"Actuals for {self.prop} — {self.month.strftime('%Y-%m')}"

    @property
    def actual_noi(self) -> Decimal:
        """Net operating income for this month."""
        return (
            self.actual_rent_collected - self.actual_expenses - self.actual_maintenance
        )

    @property
    def vacancy_rate(self) -> Decimal:
        """Vacancy rate as a fraction of the month."""
        days_in_month = 30  # Simplified; most months ~30 days
        return Decimal(str(self.actual_vacancy_days)) / Decimal(str(days_in_month))


# ═══════════════════════════════════════════════════════════════════════════
# Property Discovery Sources & Requests
# ═══════════════════════════════════════════════════════════════════════════
