from __future__ import annotations
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from core.models.property import Property, InvestmentAnalysis

User = get_user_model()


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

    # ── Location fields (populated at discovery time) ─────────────────
    city = models.CharField(
        max_length=128,
        blank=True,
        default="",
        db_index=True,
        help_text="City name copied from source record at discovery time",
    )
    state = models.CharField(
        max_length=2,
        blank=True,
        default="",
        db_index=True,
        help_text="2-letter state code copied from source record",
    )
    zip_code = models.CharField(
        max_length=16,
        blank=True,
        default="",
        db_index=True,
        help_text="ZIP code copied from source record",
    )
    county = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="County name copied from source record — links to QCEW and FMR data",
    )
    growth_area = models.ForeignKey(
        "GrowthArea",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pipeline_properties",
        help_text="Growth area this property was discovered under — set at discovery time",
    )

    # ── Pipeline stage ───────────────────────────────────────────────
    stage = models.CharField(
        max_length=20, choices=Stage.choices, default=Stage.DISCOVERED, db_index=True
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    screening_passed = models.BooleanField(null=True, blank=True, db_index=True)
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
        indexes = [
            models.Index(
                fields=["source_type", "source_id"], name="idx_pp_source_type_source_id"
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
