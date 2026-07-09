from __future__ import annotations
from django.contrib.auth import get_user_model
from django.db import models
from core.models.pipeline import ForeclosureProperty

User = get_user_model()


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
