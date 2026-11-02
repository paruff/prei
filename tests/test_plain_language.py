"""G7.4 (FR-18): no raw enum values, "Remove" not "Kill", empty states explain themselves."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from core.models import PipelineProperty
from core.templatetags.format_filters import enum_label

User = get_user_model()


@pytest.fixture
def prop(db, client):
    user = User.objects.create_user(username="pl", password="pw")
    client.force_login(user)
    return PipelineProperty.objects.create(
        user=user,
        source_type="vrm",
        source_id="900001",
        address="1 Plain St",
        address_hash="pl-hash",
        stage=PipelineProperty.Stage.DUE_DILIGENCE,
        status=PipelineProperty.Status.ACTIVE,
        discovered_at=timezone.now(),
    )


def test_enum_label_filter():
    assert enum_label("DUE_DILIGENCE") == "Due Diligence"
    assert enum_label("for_sale") == "For Sale"
    assert enum_label(None) == "—"


def test_detail_shows_words_not_enums(client, prop):
    html = client.get(reverse("pipeline_detail", args=[prop.pk])).content.decode()
    assert "Due Diligence" in html
    assert "VRM Foreclosure" in html
    for raw in ("Due_Diligence", "Vrm #", "Kill"):
        assert raw not in html


def test_acquired_badge_not_duplicated(client, prop):
    prop.stage = PipelineProperty.Stage.ACQUIRED
    prop.status = PipelineProperty.Status.ACQUIRED
    prop.save()
    html = client.get(reverse("pipeline_detail", args=[prop.pk])).content.decode()
    assert html.count("pipeline-badge badge-stage") == 1
    assert "badge-status-acquired" not in html


def test_kanban_empty_columns_use_partial(client, db):
    client.force_login(User.objects.create_user(username="pk", password="pw"))
    html = client.get(reverse("pipeline_kanban")).content.decode()
    assert "empty-state" in html
    assert "kanban-empty" not in html
    assert "{{" not in html
    assert "Kill" not in html
