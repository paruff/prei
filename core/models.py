from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
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


class Team(models.Model):
    """Collaboration team for sharing property analyses."""

    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_teams"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # noqa: D401
        return self.name


class TeamMember(models.Model):
    """Membership record for a user in a team."""

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MEMBER = "member", "Member"

    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="team_members"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="team_memberships"
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["team", "user"], name="unique_team_user"),
        ]

    def __str__(self) -> str:  # noqa: D401
        return f"{self.user.username} in {self.team.name}"


class PropertyNote(models.Model):
    """Team collaboration note attached to a property."""

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="collaboration_notes"
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="property_notes"
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class SharedProperty(models.Model):
    """Property shared to a team by a user."""

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="shared_teams"
    )
    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="shared_properties"
    )
    shared_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="shared_properties"
    )
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["property", "team"], name="unique_property_team"
            ),
        ]


class PropertyShare(models.Model):
    ROLE_CHOICES = [("team", "Team Member"), ("client", "Client")]

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="property_shares"
    )
    shared_with = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="shared_properties_access"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["property", "shared_with"], name="unique_property_shared_with"
            ),
        ]


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


class Listing(models.Model):
    """Normalized real estate listing ingested from external sources.

    Fields capture essential attributes for filtering and scoring in Phase 1.
    """

    SOURCE_CHOICES = (
        ("dummy", "Dummy"),
        ("external", "External"),
    )

    source = models.CharField(max_length=64, choices=SOURCE_CHOICES)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=128, blank=True, default="")
    state = models.CharField(max_length=64, blank=True, default="")
    zip_code = models.CharField(max_length=16, blank=True, default="")
    price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    beds = models.PositiveIntegerField(default=0)
    baths = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal("0"))
    sq_ft = models.PositiveIntegerField(default=0)
    property_type = models.CharField(max_length=64, blank=True, default="")
    url = models.URLField(unique=True)
    posted_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-posted_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.address} ({self.city}, {self.state}) - ${self.price}"


class MarketSnapshot(models.Model):
    """Normalized market/area metrics for intelligence layer.

    Represents aggregated signals for a geographic area (e.g., ZIP or city/state).
    """

    area_type = models.CharField(max_length=16, default="zip")  # zip or city
    zip_code = models.CharField(max_length=16, blank=True, default="")
    city = models.CharField(max_length=128, blank=True, default="")
    state = models.CharField(max_length=64, blank=True, default="")

    # --- Phase 0: Census & BLS market indicators ---
    msa_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Metropolitan Statistical Area name",
    )
    population = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total population for ZIP/area",
    )
    population_growth_pct_5yr = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="5-year population growth as fraction (e.g. 0.0234 = 2.34%)",
    )
    unemployment_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Unemployment rate as fraction (e.g. 0.045 = 4.5%)",
    )
    median_household_income = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Median household income in dollars",
    )
    fetched_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this data was fetched from Census/BLS APIs",
    )

    # --- Existing metrics ---
    rent_index = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    price_trend = models.DecimalField(
        max_digits=6, decimal_places=4, default=Decimal("0")
    )  # % change
    crime_score = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("0")
    )  # lower better
    school_rating = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("0")
    )
    price_to_rent_ratio = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    population_growth_rate = models.DecimalField(
        max_digits=7, decimal_places=4, null=True, blank=True
    )
    employment_diversity_score = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    landlord_friendliness_score = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    rent_growth_rate = models.DecimalField(
        max_digits=7, decimal_places=4, null=True, blank=True
    )
    market_score = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )

    updated_at = models.DateTimeField(auto_now=True)
    data_source = models.CharField(
        max_length=64,
        blank=True,
        default="dummy",
        help_text="Adapter source for this snapshot (e.g. 'rentcast', 'dummy', 'mixed')",
    )

    class Meta:
        ordering = ["-price_trend", "-rent_index"]

    def __str__(self) -> str:
        label = self.zip_code or f"{self.city}, {self.state}".strip(", ")
        return (
            f"MarketSnapshot {label} (trend={self.price_trend}, rent={self.rent_index})"
        )


class SavedSearch(models.Model):
    """Persisted search filters for listings, per user."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="saved_searches"
    )
    name = models.CharField(max_length=128)
    query = models.CharField(max_length=255, blank=True, default="")
    zip_code = models.CharField(max_length=16, blank=True, default="")
    state = models.CharField(max_length=64, blank=True, default="")
    min_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    max_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"SavedSearch {self.name} ({self.state} {self.zip_code})"


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


class AuditLog(models.Model):
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=64)
    object_type = models.CharField(max_length=64, blank=True, default="")
    object_id = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    meta = models.JSONField(default=dict)

    class Meta:
        ordering = ["-timestamp"]


class GrowthArea(models.Model):
    """Economic growth area data for real estate investment analysis."""

    state = models.CharField(max_length=2, db_index=True)
    city_name = models.CharField(max_length=255)
    metro_area = models.CharField(max_length=255, blank=True)
    population_growth_rate = models.DecimalField(max_digits=6, decimal_places=2)
    employment_growth_rate = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    median_income_growth = models.DecimalField(max_digits=6, decimal_places=2)
    housing_demand_index = models.IntegerField()
    supply_constraint_index = models.IntegerField(default=50, null=True, blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    data_timestamp = models.DateTimeField()
    population = models.IntegerField(
        null=True, blank=True, help_text="Latest population from Census ACS"
    )
    composite_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Precomputed weighted growth score (computed on save)",
    )
    landlord_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        default=None,
        help_text="State landlord-friendliness score (0=tenant-friendly, 10=landlord-friendly)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["state", "city_name"], name="unique_state_city"
            ),
        ]
        ordering = ["-data_timestamp"]

    def __str__(self) -> str:  # noqa: D401
        return f"{self.city_name}, {self.state}"

    def composite_score_display(self) -> Decimal | None:
        """Return precomputed composite score, or compute on the fly if not stored."""
        if self.composite_score is not None:
            return self.composite_score
        return self._compute_composite_score()

    def _compute_composite_score(self) -> Decimal | None:
        """Calculate composite growth score based on weighted metrics.

        Returns None if none of the weighted factors are available (all are None/zero).
        Missing factors are treated as 0 so a partial score is still computable.

        Weights (revised GA-6):
          - Population growth rate:  0.20  (place-level, Census ACS)
          - Employment growth rate:  0.35  (state-level, FRED)
          - Median income growth:    0.20  (place-level, Census ACS)
          - Housing demand index:    0.10  (place-level, Census ACS occupancy)
          - Supply constraint index: 0.15  (place-level, Census ACS housing-unit growth)
        """
        pop_weight = Decimal("0.20")
        emp_weight = Decimal("0.35")
        income_weight = Decimal("0.20")
        housing_weight = Decimal("0.10")
        supply_weight = Decimal("0.15")

        pop_rate = self.population_growth_rate or Decimal("0")
        emp_rate = self.employment_growth_rate or Decimal("0")
        income_rate = self.median_income_growth or Decimal("0")
        housing_idx = Decimal(self.housing_demand_index or 0)
        supply_idx = Decimal(self.supply_constraint_index or 0)

        score = (
            pop_rate * pop_weight
            + emp_rate * emp_weight
            + income_rate * income_weight
            + housing_idx * housing_weight
            + supply_idx * supply_weight
        )
        return score

    def save(self, *args, **kwargs):
        """Precompute composite_score on save."""
        self.composite_score = self._compute_composite_score()
        super().save(*args, **kwargs)


class PipelineAsset(models.Model):
    """Django ORM model mirroring the pipeline state machine.

    Tracks a property through the 11-stage pipeline lifecycle with
    a snapshot of the current stage and relevant financial metrics.
    """

    asset_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="External source identifier",
    )
    address = models.TextField(help_text="Raw address string")
    address_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 of normalized address for dedup",
    )
    source_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Origin source label",
    )

    STAGE_CHOICES = [
        ("GACS", "GACS"),
        ("DISCOVERY", "Discovery"),
        ("SCREENING", "Screening"),
        ("UNDERWRITING", "Underwriting"),
        ("OFFER", "Offer"),
        ("DUE_DILIGENCE", "Due Diligence"),
        ("CLOSING", "Closing"),
        ("TURNOVER", "Turnover"),
        ("LEASING", "Leasing"),
        ("PORTFOLIO", "Portfolio"),
        ("KILLED", "Killed"),
    ]
    current_stage = models.CharField(
        max_length=20,
        choices=STAGE_CHOICES,
        default="GACS",
    )
    kill_reason = models.TextField(blank=True, null=True)

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    estimated_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    noi = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    cap_rate = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
    )
    mao = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    beds = models.IntegerField(null=True, blank=True)
    baths = models.FloatField(null=True, blank=True)
    sqft = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Pipeline Asset"
        verbose_name_plural = "Pipeline Assets"

    def __str__(self) -> str:
        return f"{self.asset_id} [{self.current_stage}]"


class PipelineProperty(models.Model):
    """A property tracked through the acquisition pipeline lifecycle.

    Covers stages from raw discovery through acquisition, stabilization,
    and portfolio transfer. Each row represents a single property from a
    single source, deduplicated by (user, source_type, source_id).
    """

    class Stage(models.TextChoices):
        DISCOVERED = "DISCOVERED", "Discovered"
        SCREENING = "SCREENING", "Screening"
        UNDERWRITING = "UNDERWRITING", "Underwriting"
        OFFER = "OFFER", "Offer"
        DUE_DILIGENCE = "DUE_DILIGENCE", "Due Diligence"
        CLOSING = "CLOSING", "Closing"
        ACQUIRED = "ACQUIRED", "Acquired"
        RENOVATION = "RENOVATION", "Renovation"
        STABILIZED = "STABILIZED", "Stabilized"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        KILLED = "KILLED", "Killed"
        ON_HOLD = "ON_HOLD", "On Hold"
        ACQUIRED = "ACQUIRED", "Acquired"

    class SourceType(models.TextChoices):
        VRM = "vrm", "VRM Foreclosure"
        FORECLOSURE = "foreclosure", "County Foreclosure"
        LISTING = "listing", "MLS Listing"
        MANUAL = "manual", "Manual Entry"
        HUD = "hud", "HUD Homestore"
        USDA = "usda", "USDA Foreclosure"
        FANNIE = "fannie", "Fannie Mae HomePath"
        FREDDIE = "freddie", "Freddie Mac HomeSteps"
        COUNTY = "county", "County Records"
        BANK_REO = "bank_reo", "Bank REO"

    # ── Identity ─────────────────────────────────────────────────────
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="pipeline_properties"
    )
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    source_id = models.CharField(max_length=255)
    address = models.TextField()
    address_hash = models.CharField(
        max_length=64, db_index=True, blank=True, default=""
    )

    # ── Pipeline stage ───────────────────────────────────────────────
    stage = models.CharField(
        max_length=20, choices=Stage.choices, default=Stage.DISCOVERED
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    screening_passed = models.BooleanField(null=True, blank=True)
    kill_reason = models.TextField(blank=True, default="")

    # ── Stage timestamps (null until stage is entered) ───────────────
    discovered_at = models.DateTimeField(null=True, blank=True)
    screening_at = models.DateTimeField(null=True, blank=True)
    underwriting_at = models.DateTimeField(null=True, blank=True)
    offer_at = models.DateTimeField(null=True, blank=True)
    due_diligence_at = models.DateTimeField(null=True, blank=True)
    closing_at = models.DateTimeField(null=True, blank=True)
    acquired_at = models.DateTimeField(null=True, blank=True)
    renovation_at = models.DateTimeField(null=True, blank=True)
    stabilized_at = models.DateTimeField(null=True, blank=True)

    # ── Financial snapshot ───────────────────────────────────────────
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    estimated_rent = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    beds = models.IntegerField(null=True, blank=True)
    baths = models.FloatField(null=True, blank=True)
    sqft = models.FloatField(null=True, blank=True)
    year_built = models.IntegerField(null=True, blank=True)

    # ── Underwriting results ─────────────────────────────────────────
    investment_analysis = models.ForeignKey(
        InvestmentAnalysis,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    gacs_score = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    mao = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # ── Property record (post-acquisition, transferred to Property model) ───
    property_record = models.ForeignKey(
        Property,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    # ── Timestamps ───────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "source_type", "source_id"],
                name="unique_user_source_property",
            ),
        ]
        ordering = ["-updated_at"]
        verbose_name = "Pipeline Property"
        verbose_name_plural = "Pipeline Properties"

    def __str__(self) -> str:
        return f"{self.source_type}/{self.source_id} [{self.stage}]"


class ForeclosureProperty(models.Model):
    """Foreclosure property listing from external data sources."""

    FORECLOSURE_STATUS_CHOICES = (
        ("preforeclosure", "Pre-foreclosure"),
        ("auction", "Auction Scheduled"),
        ("reo", "Bank-owned/REO"),
        ("government", "Government-owned"),
    )

    PROPERTY_TYPE_CHOICES = (
        ("single-family", "Single Family"),
        ("condo", "Condo"),
        ("multi-family", "Multi-family"),
        ("commercial", "Commercial"),
    )

    property_id = models.CharField(max_length=128, unique=True, db_index=True)
    data_source = models.CharField(max_length=64)
    data_timestamp = models.DateTimeField()

    street = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    county = models.CharField(max_length=128, blank=True, default="")
    state = models.CharField(max_length=2, db_index=True)
    zip_code = models.CharField(max_length=16, db_index=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    foreclosure_status = models.CharField(
        max_length=32, choices=FORECLOSURE_STATUS_CHOICES, db_index=True
    )
    foreclosure_stage = models.CharField(max_length=128, blank=True, default="")
    filing_date = models.DateField(null=True, blank=True)
    auction_date = models.DateField(null=True, blank=True, db_index=True)
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
    lender_name = models.CharField(max_length=255, blank=True, default="")
    case_number = models.CharField(max_length=128, blank=True, default="")
    trustee_name = models.CharField(max_length=255, blank=True, default="")
    trustee_phone = models.CharField(max_length=32, blank=True, default="")

    property_type = models.CharField(
        max_length=32, choices=PROPERTY_TYPE_CHOICES, blank=True, default=""
    )
    bedrooms = models.PositiveIntegerField(default=0)
    bathrooms = models.DecimalField(
        max_digits=4, decimal_places=1, default=Decimal("0")
    )
    square_footage = models.PositiveIntegerField(default=0)
    lot_size = models.PositiveIntegerField(default=0)
    year_built = models.PositiveIntegerField(null=True, blank=True)
    stories = models.PositiveIntegerField(null=True, blank=True)
    garage = models.CharField(max_length=128, blank=True, default="")
    pool = models.BooleanField(default=False)
    condition = models.CharField(max_length=64, blank=True, default="")

    estimated_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    last_sale_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    last_sale_date = models.DateField(null=True, blank=True)
    tax_assessed_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    annual_taxes = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    images = models.JSONField(default=list, blank=True)
    property_detail_url = models.URLField(blank=True, default="")
    redfin_url = models.URLField(blank=True, default="")
    zillow_url = models.URLField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["auction_date", "-created_at"]
        indexes = [
            models.Index(fields=["state", "city"]),
            models.Index(fields=["foreclosure_status", "auction_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.street}, {self.city}, {self.state} {self.zip_code} - {self.foreclosure_status}"


# ═══════════════════════════════════════════════════════════════════════════
# Source-Specific Property Models (Discovery Pipeline)
# ═══════════════════════════════════════════════════════════════════════════


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


class UserWatchlist(models.Model):
    """User's watchlist for tracking specific foreclosure properties."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="watchlist")
    property = models.ForeignKey(
        ForeclosureProperty, on_delete=models.CASCADE, related_name="watchers"
    )
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "property"], name="unique_user_watchlist_property"
            ),
        ]
        ordering = ["-added_at"]

    def __str__(self) -> str:  # noqa: D401
        return f"{self.user.username} watching {self.property.street}"


class AuctionAlert(models.Model):
    """User-configured alerts for auction criteria."""

    ALERT_TYPE_CHOICES = (
        ("new_auction", "New Auction Scheduled"),
        ("status_change", "Status Change"),
        ("price_change", "Price Change"),
        ("postponement", "Postponement"),
        ("reminder", "Auction Reminder"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="alerts")
    name = models.CharField(max_length=128)
    alert_type = models.CharField(max_length=32, choices=ALERT_TYPE_CHOICES)
    is_active = models.BooleanField(default=True)

    # Criteria filters (all optional)
    states = models.JSONField(default=list, blank=True)  # List of state codes
    cities = models.JSONField(default=list, blank=True)  # List of cities
    property_types = models.JSONField(default=list, blank=True)
    min_opening_bid = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    max_opening_bid = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    radius_miles = models.PositiveIntegerField(null=True, blank=True)
    center_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    center_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    # Reminder settings
    reminder_days_before = models.JSONField(default=list, blank=True)  # e.g., [7, 3, 1]

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # noqa: D401
        return f"{self.user.username} - {self.name}"

    def matches_property(self, property: ForeclosureProperty) -> bool:
        """Check if a property matches this alert's criteria."""
        if self.states and property.state not in self.states:
            return False

        if self.cities and property.city not in self.cities:
            return False

        if self.property_types and property.property_type not in self.property_types:
            return False

        if self.min_opening_bid and property.opening_bid:
            if property.opening_bid < self.min_opening_bid:
                return False

        if self.max_opening_bid and property.opening_bid:
            if property.opening_bid > self.max_opening_bid:
                return False

        # Location-based filtering
        if (
            self.radius_miles
            and self.center_latitude
            and self.center_longitude
            and property.latitude
            and property.longitude
        ):
            from math import asin, cos, radians, sin, sqrt

            # Haversine formula for distance calculation
            lat1, lon1 = (
                radians(float(self.center_latitude)),
                radians(float(self.center_longitude)),
            )
            lat2, lon2 = (
                radians(float(property.latitude)),
                radians(float(property.longitude)),
            )

            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            c = 2 * asin(sqrt(a))
            distance_miles = 3959 * c  # Earth radius in miles

            if distance_miles > self.radius_miles:
                return False

        return True


class NotificationPreference(models.Model):
    """User preferences for notifications."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    notify_email = models.BooleanField(default=True)
    notify_sms = models.BooleanField(default=False)
    notify_push = models.BooleanField(default=False)
    notify_in_app = models.BooleanField(default=True)

    # Quiet hours (24-hour format)
    quiet_hours_start = models.TimeField(null=True, blank=True)  # e.g., 22:00
    quiet_hours_end = models.TimeField(null=True, blank=True)  # e.g., 08:00

    # Contact information
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")
    device_tokens = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # noqa: D401
        return f"Notification preferences for {self.user.username}"

    def is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours."""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False

        from django.utils import timezone

        now = timezone.now().time()

        # Handle quiet hours that span midnight
        if self.quiet_hours_start <= self.quiet_hours_end:
            return self.quiet_hours_start <= now <= self.quiet_hours_end
        else:
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end


class Notification(models.Model):
    """In-app notifications for users."""

    NOTIFICATION_TYPE_CHOICES = (
        ("auction_update", "Auction Update"),
        ("status_change", "Status Change"),
        ("postponement", "Postponement"),
        ("reminder", "Reminder"),
        ("price_change", "Price Change"),
        ("sold", "Property Sold"),
    )

    PRIORITY_CHOICES = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(
        max_length=32, choices=NOTIFICATION_TYPE_CHOICES
    )
    priority = models.CharField(
        max_length=16, choices=PRIORITY_CHOICES, default="medium"
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    property = models.ForeignKey(
        ForeclosureProperty,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    url = models.CharField(max_length=512, blank=True, default="")
    data = models.JSONField(default=dict, blank=True)

    is_read = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
        ]

    def __str__(self) -> str:  # noqa: D401
        return f"{self.user.username} - {self.title}"

    def mark_read(self) -> None:
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            from django.utils import timezone

            self.read_at = timezone.now()
            self.save()

    def dismiss(self) -> None:
        """Dismiss notification."""
        if not self.is_dismissed:
            self.is_dismissed = True
            from django.utils import timezone

            self.dismissed_at = timezone.now()
            self.save()


class UserProfile(models.Model):
    """Per-user investment preferences and tax settings."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    marginal_tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.24"),
        help_text="Marginal income-tax rate as a fraction (e.g. 0.24 for 24 %)",
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("1"))],
    )
    land_value_pct = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.20"),
        help_text="Fraction of property value attributable to land (e.g. 0.20 for 20 %)",
        validators=[
            MinValueValidator(Decimal("0")),
            MaxValueValidator(Decimal("0.99")),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # noqa: D401
        return f"Profile for {self.user.username}"

    updated_at = models.DateTimeField(auto_now=True)


class ScreeningCriteria(models.Model):
    """Per-user screening criteria for pipeline property filtering.

    Defines the structural and financial bounds used by the pipeline
    screening stage to evaluate incoming properties. One set of criteria
    per user — replaces/provides the superset of simpler per-user prefs.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="screening_criteria"
    )

    # Price range
    max_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    min_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # Yield and ratio
    min_gross_yield_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("7.00"),
        help_text="Minimum gross yield as percentage (e.g. 7.00 = 7%)",
    )
    max_price_to_rent_ratio = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("15.00"),
    )

    # Beds and size
    min_beds = models.IntegerField(default=1)
    max_beds = models.IntegerField(null=True, blank=True)
    min_sqft = models.IntegerField(null=True, blank=True)
    max_year_built = models.IntegerField(null=True, blank=True)

    # Allowed values
    allowed_property_types = models.JSONField(default=list, blank=True)
    allowed_states = models.JSONField(default=list, blank=True)
    allowed_foreclosure_statuses = models.JSONField(default=list, blank=True)

    # Score floor
    min_gacs_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum Growth Area Composite Score for the property's market",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Screening Criteria"
        verbose_name_plural = "Screening Criteria"

    def __str__(self) -> str:
        return f"{self.user.email}: yield>={self.min_gross_yield_pct}%, PTR<={self.max_price_to_rent_ratio}"


class OfferRecord(models.Model):
    """Record of an offer made on a pipeline property.

    Supports the OFFER stage of the acquisition pipeline.
    A PipelineProperty can have multiple offers (counter-offers).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        COUNTERED = "countered", "Countered"
        WITHDRAWN = "withdrawn", "Withdrawn"

    pipeline_property = models.ForeignKey(
        PipelineProperty, on_delete=models.CASCADE, related_name="offers"
    )
    offer_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    offer_date = models.DateField()
    offer_expiry = models.DateField(null=True, blank=True)
    contingencies = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    counter_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Offer Record"
        verbose_name_plural = "Offer Records"

    def __str__(self) -> str:
        return f"Offer #{self.pk}: ${self.offer_price} on {self.pipeline_property}"


class DueDiligenceChecklist(models.Model):
    """Due diligence checklist for a pipeline property.

    Tracks inspection, title, appraisal, insurance, and contractor
    tasks during the DUE_DILIGENCE stage.
    """

    class GoNoGo(models.TextChoices):
        PENDING = "pending", "Pending"
        GO = "go", "Go"
        NO_GO = "no_go", "No Go"

    pipeline_property = models.OneToOneField(
        PipelineProperty,
        on_delete=models.CASCADE,
        related_name="due_diligence",
    )
    inspection_scheduled = models.BooleanField(default=False)
    inspection_completed = models.BooleanField(default=False)
    inspection_findings = models.TextField(blank=True, default="")
    title_search_ordered = models.BooleanField(default=False)
    title_clear = models.BooleanField(null=True, blank=True)
    appraisal_ordered = models.BooleanField(default=False)
    appraisal_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    insurance_quoted = models.BooleanField(default=False)
    insurance_annual_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    contractor_estimate_obtained = models.BooleanField(default=False)
    contractor_estimate_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    go_no_go = models.CharField(
        max_length=10,
        choices=GoNoGo.choices,
        default=GoNoGo.PENDING,
    )
    no_go_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Due Diligence Checklist"
        verbose_name_plural = "Due Diligence Checklists"

    def __str__(self) -> str:
        return f"DD #{self.pk}: {self.go_no_go} for {self.pipeline_property}"


class ClosingRecord(models.Model):
    """Closing record for an acquired pipeline property.

    Captures final purchase price, closing costs, loan details,
    and related metadata from the CLOSING stage.
    """

    pipeline_property = models.OneToOneField(
        PipelineProperty,
        on_delete=models.CASCADE,
        related_name="closing_record",
    )
    final_purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    closing_date = models.DateField()
    closing_costs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    loan_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    down_payment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    lender = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Closing Record"
        verbose_name_plural = "Closing Records"

    def __str__(self) -> str:
        return (
            f"Closing #{self.pk}: ${self.final_purchase_price} on {self.closing_date}"
        )


class RenovationRecord(models.Model):
    """Renovation record for a pipeline property post-acquisition.

    Tracks budget, actual costs, timeline, and scope of work during
    the RENOVATION stage. Links to both PipelineProperty (during
    pipeline) and Property (post-conversion).
    """

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETE = "complete", "Complete"

    pipeline_property = models.OneToOneField(
        PipelineProperty,
        on_delete=models.CASCADE,
        related_name="renovation_record",
    )
    property_record = models.ForeignKey(
        Property,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="renovations",
    )
    estimated_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    actual_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    start_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    contractor = models.CharField(max_length=255, blank=True, default="")
    scope_of_work = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Renovation Record"
        verbose_name_plural = "Renovation Records"

    def __str__(self) -> str:
        return f"Renovation #{self.pk}: {self.status} ({self.estimated_budget})"


class LeasingPipelineProperty(models.Model):
    """A property in the leasing pipeline (post-acquisition).

    Triggered when RenovationRecord.status = complete or manually.
    Tracks the tenant acquisition process from listing through
    lease signing and move-in to stabilization.
    """

    class Stage(models.TextChoices):
        LISTING = "LISTING", "Listed / Marketing"
        SHOWING = "SHOWING", "Showings Scheduled"
        APPLICATION = "APPLICATION", "Application Received"
        SCREENING = "SCREENING", "Applicant Screening"
        APPROVED = "APPROVED", "Applicant Approved"
        LEASE_SIGNED = "LEASE_SIGNED", "Lease Signed"
        MOVE_IN = "MOVE_IN", "Move-In Complete"
        STABILIZED = "STABILIZED", "Stabilized"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        FILLED = "FILLED", "Unit Filled"
        ON_HOLD = "ON_HOLD", "On Hold"

    property_record = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="leasing_entries",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="leasing_properties",
    )

    stage = models.CharField(
        max_length=20,
        choices=Stage.choices,
        default=Stage.LISTING,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    # Listing details
    asking_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    listed_date = models.DateField(null=True, blank=True)
    listing_source = models.CharField(max_length=128, blank=True, default="")

    # Applicant tracking
    applicant_name = models.CharField(max_length=128, blank=True, default="")
    application_date = models.DateField(null=True, blank=True)
    screening_passed = models.BooleanField(null=True)
    screening_notes = models.TextField(blank=True, default="")

    # Lease details
    lease_start_date = models.DateField(null=True, blank=True)
    lease_end_date = models.DateField(null=True, blank=True)
    monthly_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    security_deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    # Move-in
    move_in_date = models.DateField(null=True, blank=True)
    stabilized_date = models.DateField(null=True, blank=True)

    # Stage timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Leasing Pipeline Property"
        verbose_name_plural = "Leasing Pipeline Properties"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Leasing #{self.pk}: {self.property_record} [{self.stage}]"


class UserScreeningPreferences(models.Model):
    """Per-user screening thresholds for pipeline discovery."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="screening_preferences"
    )
    min_gross_yield = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.07"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("1"))],
    )
    max_price_to_rent_ratio = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("15.00"),
        validators=[MinValueValidator(Decimal("1")), MaxValueValidator(Decimal("100"))],
    )
    min_beds = models.PositiveIntegerField(default=1)
    min_baths = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Screening Preferences"
        verbose_name_plural = "Screening Preferences"

    def __str__(self) -> str:
        return (
            f"{self.user.email}: yield>={self.min_gross_yield}, "
            f"PTR<={self.max_price_to_rent_ratio}"
        )


class UserInvestmentTargets(models.Model):
    """Per-user configurable underwriting thresholds and assumptions."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="investment_targets"
    )

    # Buy/no-buy thresholds
    min_coc_pct = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.08"),
        help_text="Minimum Cash-on-Cash return as a fraction (e.g. 0.08 for 8 %)",
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("1"))],
    )
    min_dscr = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("1.25"),
        help_text="Minimum Debt Service Coverage Ratio (e.g. 1.25)",
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("10"))],
    )
    max_grm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("12.00"),
        help_text="Maximum Gross Rent Multiplier — lower is better (e.g. 12.0)",
        validators=[MinValueValidator(Decimal("1")), MaxValueValidator(Decimal("100"))],
    )
    require_one_pct_rule = models.BooleanField(
        default=True,
        help_text="If enabled, properties failing the 1% Rule are capped at 40 points",
    )
    target_hold_years = models.PositiveIntegerField(default=7)
    annual_rent_growth_assumption = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.03"),
        help_text="Assumed annual rent growth as a fraction",
    )
    annual_appreciation_assumption = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.03"),
        help_text="Assumed annual appreciation as a fraction",
    )
    marginal_tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.24"),
        help_text="Marginal income-tax rate as a fraction",
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("1"))],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # noqa: D401
        return f"Investment targets for {self.user.username}"


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


class PropertySource(models.Model):
    """A discoverable source of properties that feeds into the pipeline.

    Each row corresponds to one of the ``PipelineProperty.SourceType``
    choices and tracks whether a working integration exists, where to find
    it online, and basic metadata for the discovery UI.

    Users browse available sources on the Property Discovery page and
    submit ``DiscoveryRequest`` records to trigger property fetching from a
    source for a specific location.
    """

    source_type = models.CharField(
        max_length=20,
        choices=PipelineProperty.SourceType.choices,
        unique=True,
        help_text="Maps to PipelineProperty.SourceType",
    )
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default="")
    website_url = models.URLField(blank=True, default="")
    is_free = models.BooleanField(default=True)
    is_active = models.BooleanField(
        default=False,
        help_text="Has a working scraper or API integration",
    )
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Property Source"
        verbose_name_plural = "Property Sources"

    def __str__(self) -> str:
        return self.name


class DiscoveryRequest(models.Model):
    """A user-initiated request to discover properties from a source.

    When a user clicks 'Request Properties' on a source in the Property
    Discovery page, a ``DiscoveryRequest`` is created.  Future scrapers
    and ingesters will pick up ``REQUESTED`` records, fetch properties
    for the target location, and create ``PipelineProperty`` records
    from the results.
    """

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="discovery_requests"
    )
    source = models.ForeignKey(
        PropertySource, on_delete=models.CASCADE, related_name="requests"
    )
    location = models.CharField(
        max_length=255, help_text="City, State or ZIP code to target"
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.REQUESTED
    )
    properties_found = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Discovery Request"
        verbose_name_plural = "Discovery Requests"

    def __str__(self) -> str:
        return f"{self.source.name} @ {self.location} [{self.status}]"
