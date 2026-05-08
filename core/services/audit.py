"""Audit logging services."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from django.db import models

from core.models import AuditLog


def log_action(
    user: User | None,
    action: str,
    obj: object | None = None,
    meta: dict[str, Any] | None = None,
) -> AuditLog:
    """Create an audit log entry for a user action."""
    object_id = getattr(obj, "id", None) if obj is not None else None
    object_type = ""
    if obj is not None:
        if isinstance(obj, models.Model):
            object_type = str(obj._meta.object_name)
        else:
            object_type = obj.__class__.__name__

    return AuditLog.objects.create(
        user=user,
        action=action,
        object_type=object_type,
        object_id=object_id if isinstance(object_id, int) else None,
        meta=meta or {},
    )
