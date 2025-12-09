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
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2)
    purchase_date = models.DateField(null=True, blank=True)
    sqft = models.IntegerField(null=True, blank=True)
    units = models.IntegerField(default=1)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:  # noqa: D401
        return f"{self.address}, {self.city}, {self.state} {self.zip_code}"


class RentalIncome(models.Model):
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="rental_incomes"
    )
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

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-price_trend", "-rent_index"]

    def __str__(self) -> str:
        label = self.zip_code or f"{self.city}, {self.state}".strip(", ")
        return (
            f"MarketSnapshot {label} (trend={self.price_trend}, rent={self.rent_index})"
        )


class GrowthArea(models.Model):
    """Economic growth area data for real estate investment analysis."""

    state = models.CharField(max_length=2, db_index=True)
    city_name = models.CharField(max_length=255)
    metro_area = models.CharField(max_length=255, blank=True)
    population_growth_rate = models.DecimalField(max_digits=6, decimal_places=2)
    employment_growth_rate = models.DecimalField(max_digits=6, decimal_places=2)
    median_income_growth = models.DecimalField(max_digits=6, decimal_places=2)
    housing_demand_index = models.IntegerField()
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    data_timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["state", "city_name"]]
        ordering = ["-data_timestamp"]

    def __str__(self) -> str:  # noqa: D401
        return f"{self.city_name}, {self.state}"

    @property
    def composite_score(self) -> Decimal:
        """Calculate composite growth score based on weighted metrics."""
        pop_weight = Decimal("0.25")
        emp_weight = Decimal("0.35")
        income_weight = Decimal("0.25")
        housing_weight = Decimal("0.15")

        score = (
            self.population_growth_rate * pop_weight
            + self.employment_growth_rate * emp_weight
            + self.median_income_growth * income_weight
            + Decimal(self.housing_demand_index) * housing_weight
        )
        return score


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

    # Property ID and metadata
    property_id = models.CharField(max_length=128, unique=True, db_index=True)
    data_source = models.CharField(max_length=64)
    data_timestamp = models.DateTimeField()

    # Address information
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

    # Foreclosure details
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

    # Property details
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

    # Valuation data
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

    # Links and images
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

    def __str__(self) -> str:  # noqa: D401
        return f"{self.street}, {self.city}, {self.state} {self.zip_code} - {self.foreclosure_status}"


class UserWatchlist(models.Model):
    """User's watchlist for tracking specific foreclosure properties."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="watchlist")
    property = models.ForeignKey(
        ForeclosureProperty, on_delete=models.CASCADE, related_name="watchers"
    )
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        unique_together = [["user", "property"]]
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
            lat1, lon1 = radians(float(self.center_latitude)), radians(
                float(self.center_longitude)
            )
            lat2, lon2 = radians(float(property.latitude)), radians(
                float(property.longitude)
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
