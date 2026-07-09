from __future__ import annotations
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from core.models.property import Property

User = get_user_model()


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
