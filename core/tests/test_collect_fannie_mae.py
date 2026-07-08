"""Tests for collect_fannie_mae management command."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from core.models import DiscoveryRequest, PipelineProperty, PropertySource


@pytest.fixture
def fannie_source(db) -> PropertySource:  # type: ignore[misc]
    return PropertySource.objects.get(source_type="fannie")


@pytest.fixture
def pending_request(db, fannie_source, django_user_model) -> DiscoveryRequest:  # type: ignore[misc]
    user = django_user_model.objects.create_user(
        username="testuser", email="test@example.com", password="testpass"
    )
    return DiscoveryRequest.objects.create(
        user=user,
        source=fannie_source,
        location="Austin, TX",
        status=DiscoveryRequest.Status.REQUESTED,
    )


# Sample listing data returned by the mocked client
_SAMPLE_LISTINGS = [
    {
        "source": "fannie_mae",
        "address": "123 Main St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "price": Decimal("250000"),
        "beds": 3,
        "baths": Decimal("2"),
        "sq_ft": 1500,
        "property_type": "SFH",
        "url": "https://www.homepath.com/listing/abc123",
        "status": "Active",
    },
    {
        "source": "fannie_mae",
        "address": "456 Oak Ave",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78702",
        "price": Decimal("185000"),
        "beds": 2,
        "baths": Decimal("1"),
        "sq_ft": 950,
        "property_type": "SFH",
        "url": "https://www.homepath.com/listing/def456",
        "status": "Active",
    },
]


# ---------------------------------------------------------------------------
# --location flag
# ---------------------------------------------------------------------------


class TestLocationFlag:
    def test_creates_pipeline_properties(self, db, django_user_model) -> None:  # type: ignore[misc]
        """--location creates PipelineProperty records."""
        django_user_model.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        """--location creates PipelineProperty records."""
        with patch(
            "core.management.commands.collect_fannie_mae.FannieMaeHomePathClient"
        ) as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.search_by_location.return_value = _SAMPLE_LISTINGS

            call_command("collect_fannie_mae", location="Austin, TX")

        props = PipelineProperty.objects.filter(
            source_type=PipelineProperty.SourceType.FANNIE
        )
        assert props.count() == 2

        addresses = {p.address for p in props}
        assert "123 Main St" in addresses
        assert "456 Oak Ave" in addresses

    def test_sets_fannie_source_type(self, db, django_user_model) -> None:  # type: ignore[misc]
        """All created properties have source_type='fannie'."""
        django_user_model.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        with patch(
            "core.management.commands.collect_fannie_mae.FannieMaeHomePathClient"
        ) as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.search_by_location.return_value = _SAMPLE_LISTINGS

            call_command("collect_fannie_mae", location="Austin, TX")

        for prop in PipelineProperty.objects.all():
            assert prop.source_type == PipelineProperty.SourceType.FANNIE

    def test_sets_discovered_stage(self, db, django_user_model) -> None:  # type: ignore[misc]
        """All created properties are in the DISCOVERED stage."""
        django_user_model.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        with patch(
            "core.management.commands.collect_fannie_mae.FannieMaeHomePathClient"
        ) as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.search_by_location.return_value = _SAMPLE_LISTINGS

            call_command("collect_fannie_mae", location="Austin, TX")

        for prop in PipelineProperty.objects.all():
            assert prop.stage == PipelineProperty.Stage.DISCOVERED


# ---------------------------------------------------------------------------
# --request-id flag
# ---------------------------------------------------------------------------


class TestRequestIdFlag:
    def test_fulfills_specific_request(  # type: ignore[misc]
        self, db, pending_request
    ):
        """--request-id fulfills the specific DiscoveryRequest."""
        with patch(
            "core.management.commands.collect_fannie_mae.FannieMaeHomePathClient"
        ) as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.search_by_location.return_value = _SAMPLE_LISTINGS

            call_command("collect_fannie_mae", request_id=pending_request.id)

        pending_request.refresh_from_db()
        assert pending_request.status == DiscoveryRequest.Status.COMPLETED
        assert pending_request.properties_found == 2
        assert pending_request.completed_at is not None

    def test_creates_properties_for_request_user(  # type: ignore[misc]
        self, db, pending_request
    ):
        """Properties are created for the DiscoveryRequest's user."""
        with patch(
            "core.management.commands.collect_fannie_mae.FannieMaeHomePathClient"
        ) as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.search_by_location.return_value = _SAMPLE_LISTINGS

            call_command("collect_fannie_mae", request_id=pending_request.id)

        props = PipelineProperty.objects.filter(
            source_type=PipelineProperty.SourceType.FANNIE
        )
        assert all(p.user == pending_request.user for p in props)

    def test_errors_on_wrong_source(  # type: ignore[misc]
        self, db, pending_request
    ):
        """Request for a non-Fannie source raises CommandError."""
        # Change the source type
        other_source = PropertySource.objects.get(source_type="vrm")
        pending_request.source = other_source
        pending_request.save()

        with pytest.raises(CommandError):
            call_command("collect_fannie_mae", request_id=pending_request.id)


# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------


class TestDedup:
    def test_skips_duplicate_addresses(self, db, django_user_model) -> None:  # type: ignore[misc]
        """Same address + same user → second run skips duplicates."""
        user = django_user_model.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        # Create an existing property with the same address
        PipelineProperty.objects.create(
            user=user,
            source_type=PipelineProperty.SourceType.FANNIE,
            source_id="56c65c755e0f933a827596ec3a6c3803309cc84fff560c0de3671d3dae4e7923",
            address="123 Main St",
            address_hash="56c65c755e0f933a827596ec3a6c3803309cc84fff560c0de3671d3dae4e7923",
            stage=PipelineProperty.Stage.DISCOVERED,
            status=PipelineProperty.Status.ACTIVE,
            discovered_at=timezone.now(),
        )

        with patch(
            "core.management.commands.collect_fannie_mae.FannieMaeHomePathClient"
        ) as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.search_by_location.return_value = _SAMPLE_LISTINGS

            call_command("collect_fannie_mae", location="Austin, TX")

        # The 123 Main St listing should be skipped (dup), 456 Oak Ave should be new
        props = PipelineProperty.objects.filter(
            source_type=PipelineProperty.SourceType.FANNIE
        )
        assert props.count() == 2  # 1 existing + 1 new (456 Oak Ave)


# ---------------------------------------------------------------------------
# Empty / blocked results
# ---------------------------------------------------------------------------


class TestEmptyResults:
    def test_handles_empty_listings(  # type: ignore[misc]
        self, db, pending_request
    ):
        """Empty results from the client don't crash the command."""
        with patch(
            "core.management.commands.collect_fannie_mae.FannieMaeHomePathClient"
        ) as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.search_by_location.return_value = []

            call_command("collect_fannie_mae", request_id=pending_request.id)

        pending_request.refresh_from_db()
        assert pending_request.status == DiscoveryRequest.Status.COMPLETED
        assert pending_request.properties_found == 0
