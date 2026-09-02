from __future__ import annotations

from typing import Protocol

from core.models import (
    Property,
    PropertyShare,
)

ROLE_RANK = {"client": 1, "team": 2, "owner": 3}


class AuthenticatedUser(Protocol):
    """Minimal authenticated-user contract used by RBAC helper functions.

    The RBAC helpers only require a persisted integer ``id`` and do not depend on
    ``AbstractBaseUser`` fields, which avoids ORM typing mismatches in mypy while
    remaining compatible with configured auth user models.

    Attributes:
        id: Persisted primary key for the authenticated user.
    """

    id: int


def _get_property_role(user: AuthenticatedUser, property_obj: Property) -> str | None:
    """Return the caller's role for the property, if any.

    Args:
        user: Authenticated request user with a persisted integer id.
        property_obj: Property being authorized.

    Returns:
        str | None: "owner", "team", or "client" when access exists; otherwise None.
    """
    if property_obj.user_id == user.id:
        return "owner"
    share = PropertyShare.objects.filter(
        property=property_obj, shared_with_id=user.id
    ).first()
    if share is None:
        return None
    return share.role


def is_owner_or_shared(
    user: AuthenticatedUser, property_obj: Property, min_role: str = "client"
) -> bool:
    """Check whether user meets or exceeds the minimum property access role.

    Args:
        user: Authenticated request user with a persisted integer id.
        property_obj: Property being authorized.
        min_role: Minimum accepted role ("client", "team", or "owner").

    Returns:
        bool: True when the user's role rank is at least min_role; otherwise False.
    """
    role = _get_property_role(user, property_obj)
    if role is None:
        return False
    return ROLE_RANK[role] >= ROLE_RANK[min_role]


def _is_client_only_user(user: AuthenticatedUser) -> bool:
    """Return True when user only has client-level shared access.

    Args:
        user: Authenticated request user with a persisted integer id.

    Returns:
        bool: True when the user owns no properties and has no team-level shares.
    """
    if Property.objects.filter(user_id=user.id).exists():
        return False
    if PropertyShare.objects.filter(shared_with_id=user.id, role="team").exists():
        return False
    return PropertyShare.objects.filter(shared_with_id=user.id, role="client").exists()
