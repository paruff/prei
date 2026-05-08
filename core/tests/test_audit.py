from __future__ import annotations

import pytest

from core.models import AuditLog
from core.services.audit import log_action


@pytest.mark.django_db
def test_log_action_creates_record_with_object_metadata(user) -> None:
    audit_log = log_action(user=user, action="saved_search.created", obj=user)

    assert audit_log.action == "saved_search.created"
    assert audit_log.object_type == "User"
    assert audit_log.object_id == user.id


@pytest.mark.django_db
def test_log_action_with_null_user_creates_record() -> None:
    audit_log = log_action(user=None, action="system.maintenance")

    assert audit_log.user is None
    assert audit_log.action == "system.maintenance"


@pytest.mark.django_db
def test_audit_log_query_by_user_and_action_returns_expected_records(user) -> None:
    log_action(user=user, action="listing.saved")
    log_action(user=user, action="saved_search.created")

    logs = AuditLog.objects.filter(user=user, action="listing.saved")

    assert logs.count() == 1
    assert logs.first() is not None
    assert logs.first().action == "listing.saved"
