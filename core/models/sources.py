from __future__ import annotations
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

User = get_user_model()


class VrmPropertyProfitableManager(models.Manager["VrmProperty"]):
    """Return only VRM properties that meet the configured profit target."""

    def get_queryset(self) -> models.QuerySet["VrmProperty"]:
        return super().get_queryset().filter(meets_profit_target=True)


class VrmProperty(models.Model):
    """VA REO property listing persisted from VRM Properties."""

    class Status(models.TextChoices):
        FOR_SALE = "for_sale", "For Sale"
        COMING_SOON = "coming_soon", "Coming Soon"
        PENDING = "pending", "Pending"
        SOLD = "sold", "Sold"

    class ListingType(models.TextChoices):
        TRADITIONAL = "traditional", "Traditional"
        ONLINE_AUCTION = "online_auction", "Online Auction"
        IN_PERSON_AUCTION = "in_person_auction", "In-person Auction"

    vrm_property_id = models.IntegerField(unique=True)
    vrm_listing_url = models.URLField()
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=2)
    zip_code = models.CharField(max_length=16)
    county = models.CharField(max_length=128, null=True, blank=True)
    list_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    projected_monthly_rent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    estimated_rehab = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    gross_annual_rent = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )
    effective_gross_rent = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )
    annual_expenses = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )
    noi = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    total_investment = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )
    cap_rate = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0"))
    profit_margin_pct = models.DecimalField(
        max_digits=7, decimal_places=2, default=Decimal("0")
    )
    meets_profit_target = models.BooleanField(default=False)
    bedrooms = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    bathrooms = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    square_feet = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    lot_size_sf = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    year_built = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(1)]
    )
    property_type = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices)
    listing_type = models.CharField(
        max_length=32, choices=ListingType.choices, null=True, blank=True
    )
    vendee_eligible = models.BooleanField(default=False)
    occupied = models.BooleanField(null=True, blank=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("-90")),
            MaxValueValidator(Decimal("90")),
        ],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("-180")),
            MaxValueValidator(Decimal("180")),
        ],
    )
    mls_id = models.CharField(max_length=128, null=True, blank=True)
    parcel_number = models.CharField(max_length=128, null=True, blank=True)
    days_on_site = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    scraped_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    objects = models.Manager["VrmProperty"]()
    profitable_candidates = VrmPropertyProfitableManager()

    class Meta:
        db_table = "vrm_property"

    def __str__(self) -> str:  # noqa: D401
        return f"{self.address}, {self.city}, {self.state}"

    def calculate_profitability(self) -> None:
        """Calculate and persist profitability metrics for this property."""
        vacancy_rate_pct = Decimal(str(getattr(settings, "VACANCY_RATE_PCT", 8)))
        management_fee_pct = Decimal(str(getattr(settings, "MGMT_FEE_PCT", 10)))
        maintenance_pct_of_value = Decimal(
            str(getattr(settings, "MAINTENANCE_PCT_OF_VALUE", 1))
        )
        insurance_annual = Decimal(str(getattr(settings, "INSURANCE_ANNUAL", 1200)))
        tax_rate_pct = Decimal(str(getattr(settings, "TAX_RATE_PCT", 1.2)))
        min_profit_margin_pct = Decimal(
            str(getattr(settings, "MIN_PROFIT_MARGIN_PCT", 10))
        )

        rent = self.projected_monthly_rent or Decimal("0")
        list_price = self.list_price or Decimal("0")
        rehab = self.estimated_rehab or Decimal("0")

        gross_annual_rent = rent * Decimal("12")
        effective_gross_rent = gross_annual_rent * (
            Decimal("1") - (vacancy_rate_pct / Decimal("100"))
        )
        management = effective_gross_rent * (management_fee_pct / Decimal("100"))
        maintenance = list_price * (maintenance_pct_of_value / Decimal("100"))
        taxes = list_price * (tax_rate_pct / Decimal("100"))
        annual_expenses = management + maintenance + insurance_annual + taxes
        noi = effective_gross_rent - annual_expenses
        total_investment = list_price + rehab

        cap_rate = (
            (noi / total_investment) * Decimal("100")
            if total_investment != Decimal("0")
            else Decimal("0")
        )
        profit_margin_pct = (
            (noi / effective_gross_rent) * Decimal("100")
            if effective_gross_rent != Decimal("0")
            else Decimal("0")
        )

        self.gross_annual_rent = gross_annual_rent.quantize(Decimal("0.01"))
        self.effective_gross_rent = effective_gross_rent.quantize(Decimal("0.01"))
        self.annual_expenses = annual_expenses.quantize(Decimal("0.01"))
        self.noi = noi.quantize(Decimal("0.01"))
        self.total_investment = total_investment.quantize(Decimal("0.01"))
        self.cap_rate = cap_rate.quantize(Decimal("0.01"))
        self.profit_margin_pct = profit_margin_pct.quantize(Decimal("0.01"))
        self.meets_profit_target = self.profit_margin_pct >= min_profit_margin_pct
        self.save(
            update_fields=[
                "gross_annual_rent",
                "effective_gross_rent",
                "annual_expenses",
                "noi",
                "total_investment",
                "cap_rate",
                "profit_margin_pct",
                "meets_profit_target",
            ]
        )


class HudProperty(models.Model):
    """HUD Homestore REO property listing from public government source."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING = "pending", "Pending"
        SOLD = "sold", "Sold"
        CONTINGENT = "contingent", "Contingent"
        REMOVED = "removed", "Removed"

    class InsuredStatus(models.TextChoices):
        FHA_INSURED = "fha_insured", "FHA Insured"
        CONVENTIONAL = "conventional", "Conventional"
        UNINSURED = "uninsured", "Uninsured"
        VA = "va", "VA"

    hud_case_number = models.CharField(max_length=64, unique=True, db_index=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=2, db_index=True)
    zip_code = models.CharField(max_length=16)
    county = models.CharField(max_length=128, blank=True, default="")
    asking_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    list_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    bedrooms = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    bathrooms = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    square_feet = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    property_type = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=32, choices=Status.choices)
    insured_status = models.CharField(
        max_length=32,
        choices=InsuredStatus.choices,
        blank=True,
        default="",
    )
    listing_url = models.URLField(blank=True, default="")
    image_url = models.URLField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    scraped_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "HUD Property"
        verbose_name_plural = "HUD Properties"
        indexes = [
            models.Index(fields=["state", "city"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"HUD {self.hud_case_number} — {self.address}, {self.city}"


class UsdaProperty(models.Model):
    """USDA Rural Development REO property listing from public government source."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING = "pending", "Pending"
        SOLD = "sold", "Sold"
        REMOVED = "removed", "Removed"

    usda_case_number = models.CharField(max_length=64, unique=True, db_index=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=2, db_index=True)
    zip_code = models.CharField(max_length=16)
    county = models.CharField(max_length=128, blank=True, default="")
    list_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    bedrooms = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    bathrooms = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    square_feet = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(0)]
    )
    lot_size_acres = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    property_type = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=32, choices=Status.choices)
    listing_url = models.URLField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    scraped_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "USDA Property"
        verbose_name_plural = "USDA Properties"
        indexes = [
            models.Index(fields=["state", "city"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"USDA {self.usda_case_number} — {self.address}, {self.city}"


class CountyForeclosureNotice(models.Model):
    """Public foreclosure notice from county records (NOD, NTS, Sheriff Sale)."""

    class DocumentType(models.TextChoices):
        NOD = "nod", "Notice of Default"
        NTS = "nts", "Notice of Trustee Sale"
        SHERIFF_SALE = "sheriff_sale", "Sheriff Sale"
        LIS_PENDENS = "lis_pendens", "Lis Pendens"
        AUCTION = "auction", "Auction Calendar"

    case_number = models.CharField(max_length=128, unique=True, db_index=True)
    document_type = models.CharField(max_length=32, choices=DocumentType.choices)
    borrower_name = models.CharField(max_length=255, blank=True, default="")
    lender_name = models.CharField(max_length=255, blank=True, default="")
    trustee_name = models.CharField(max_length=255, blank=True, default="")
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=2, db_index=True)
    zip_code = models.CharField(max_length=16, blank=True, default="")
    county = models.CharField(max_length=128, db_index=True)
    filing_date = models.DateField(null=True, blank=True)
    sale_date = models.DateField(null=True, blank=True, db_index=True)
    auction_time = models.CharField(max_length=64, blank=True, default="")
    auction_location = models.TextField(blank=True, default="")
    opening_bid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    unpaid_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    estimated_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    parcel_number = models.CharField(max_length=128, blank=True, default="")
    source_url = models.URLField(blank=True, default="")
    raw_data = models.JSONField(default=dict, blank=True)
    scraped_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "County Foreclosure Notice"
        verbose_name_plural = "County Foreclosure Notices"
        ordering = ["-sale_date", "-filing_date"]
        indexes = [
            models.Index(fields=["county", "state"]),
            models.Index(fields=["document_type"]),
            models.Index(fields=["sale_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_document_type_display()} — {self.case_number} ({self.county}, {self.state})"
