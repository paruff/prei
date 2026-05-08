"""Audit logging services."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AbstractBaseUser

from core.models import AuditLog


def log_action(
    user: AbstractBaseUser | None,
    action: str,
    obj: object | None = None,
    meta: dict[str, Any] | None = None,
) -> AuditLog:
    """Create an audit log entry for a user action."""
    object_id = getattr(obj, "id", None) if obj is not None else None

    return AuditLog.objects.create(
        user=user,
        action=action,
        object_type=(obj.__class__.__name__ if obj is not None else ""),
        object_id=object_id if isinstance(object_id, int) else None,
        meta=meta or {},
    )
