"""Collaboration services for team sharing and property notes."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

from core.models import Property, PropertyNote, SharedProperty, Team


def share_property_with_team(
    property: Property, team: Team, shared_by: Any
) -> SharedProperty:
    """Share a property with a team (idempotent on property/team pair)."""
    shared_property, _ = SharedProperty.objects.update_or_create(
        property=property,
        team=team,
        defaults={"shared_by": shared_by},
    )
    return shared_property


def add_note(property: Property, author: Any, body: str) -> PropertyNote:
    """Add a collaboration note for a property."""
    return PropertyNote.objects.create(property=property, author=author, body=body)


def get_team_properties(team: Team) -> QuerySet[Property]:
    """Return all properties shared with the given team."""
    return Property.objects.filter(shared_teams__team=team).distinct()
