from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.consumers import AuctionConsumer
from core.models import ForeclosureProperty, UserWatchlist

User = get_user_model()

pytestmark = [pytest.mark.asyncio, pytest.mark.skip(reason="WebSocket tests require Redis server")]


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def foreclosure_property(db):
    """Create a test foreclosure property."""
    return ForeclosureProperty.objects.create(
        property_id="TEST001",
        data_source="test",
        data_timestamp=timezone.now(),
        street="123 Test St",
        city="Test City",
        state="CA",
        zip_code="90210",
        foreclosure_status="auction",
        auction_date=timezone.now().date() + timedelta(days=7),
        opening_bid=Decimal("250000.00"),
    )


@pytest.fixture
def mock_channel_layer():
    """Mock channel layer to avoid Redis connection during tests."""
    with patch("channels.layers.get_channel_layer") as mock_get_layer:
        mock_layer = Mock()
        mock_layer.group_add = AsyncMock()
        mock_layer.group_discard = AsyncMock()
        mock_layer.group_send = AsyncMock()
        mock_get_layer.return_value = mock_layer
        yield mock_layer


class TestAuctionConsumer:
    """Test WebSocket consumer for auction updates."""

    async def test_websocket_connection_unauthenticated(self, db):
        """Test WebSocket rejects unauthenticated connections."""
        communicator = WebsocketCommunicator(AuctionConsumer.as_asgi(), "/ws/auctions/")
        communicator.scope["user"] = Mock(is_authenticated=False)

        connected, _ = await communicator.connect()
        assert not connected

    async def test_websocket_connection_authenticated(self, user, mock_channel_layer):
        """Test WebSocket accepts authenticated connections."""
        communicator = WebsocketCommunicator(AuctionConsumer.as_asgi(), "/ws/auctions/")
        communicator.scope["user"] = user

        connected, _ = await communicator.connect()
        assert connected

        # Should receive initial state
        response = await communicator.receive_json_from()
        assert response["type"] == "initial_state"
        assert "auctions" in response

        await communicator.disconnect()

    async def test_websocket_ping_pong(self, user, mock_channel_layer):
        """Test ping/pong heartbeat mechanism."""
        communicator = WebsocketCommunicator(AuctionConsumer.as_asgi(), "/ws/auctions/")
        communicator.scope["user"] = user

        await communicator.connect()

        # Consume initial state
        await communicator.receive_json_from()

        # Send ping
        await communicator.send_json_to({"type": "ping"})

        # Should receive pong
        response = await communicator.receive_json_from()
        assert response["type"] == "pong"

        await communicator.disconnect()

    async def test_subscribe_to_property(self, user, foreclosure_property, mock_channel_layer):
        """Test subscribing to a property via WebSocket."""
        communicator = WebsocketCommunicator(AuctionConsumer.as_asgi(), "/ws/auctions/")
        communicator.scope["user"] = user

        await communicator.connect()

        # Consume initial state
        await communicator.receive_json_from()

        # Subscribe to property
        await communicator.send_json_to(
            {"type": "subscribe", "propertyId": str(foreclosure_property.id)}
        )

        # Should receive subscription confirmation
        response = await communicator.receive_json_from()
        assert response["type"] == "subscribe_response"
        assert response["propertyId"] == str(foreclosure_property.id)
        assert response["success"] is True

        # Verify watchlist entry created
        @database_sync_to_async
        def check_watchlist():
            return UserWatchlist.objects.filter(
                user=user, property=foreclosure_property
            ).exists()

        assert await check_watchlist()

        await communicator.disconnect()

    async def test_unsubscribe_from_property(self, user, foreclosure_property, mock_channel_layer):
        """Test unsubscribing from a property via WebSocket."""
        # Create watchlist entry first
        @database_sync_to_async
        def create_watchlist():
            return UserWatchlist.objects.create(user=user, property=foreclosure_property)

        await create_watchlist()

        communicator = WebsocketCommunicator(AuctionConsumer.as_asgi(), "/ws/auctions/")
        communicator.scope["user"] = user

        await communicator.connect()

        # Consume initial state
        await communicator.receive_json_from()

        # Unsubscribe from property
        await communicator.send_json_to(
            {"type": "unsubscribe", "propertyId": str(foreclosure_property.id)}
        )

        # Should receive unsubscription confirmation
        response = await communicator.receive_json_from()
        assert response["type"] == "unsubscribe_response"
        assert response["propertyId"] == str(foreclosure_property.id)
        assert response["success"] is True

        # Verify watchlist entry removed
        @database_sync_to_async
        def check_watchlist():
            return UserWatchlist.objects.filter(
                user=user, property=foreclosure_property
            ).exists()

        assert not await check_watchlist()

        await communicator.disconnect()

    async def test_initial_state_includes_watchlist(self, user, foreclosure_property, mock_channel_layer):
        """Test initial state includes user's watchlist."""
        # Create watchlist entry
        @database_sync_to_async
        def create_watchlist():
            return UserWatchlist.objects.create(user=user, property=foreclosure_property)

        await create_watchlist()

        communicator = WebsocketCommunicator(AuctionConsumer.as_asgi(), "/ws/auctions/")
        communicator.scope["user"] = user

        await communicator.connect()

        # Should receive initial state with watchlist
        response = await communicator.receive_json_from()
        assert response["type"] == "initial_state"
        assert len(response["auctions"]) == 1
        assert response["auctions"][0]["propertyId"] == str(foreclosure_property.id)
        assert response["auctions"][0]["street"] == "123 Test St"

        await communicator.disconnect()

    async def test_invalid_json_handling(self, user, mock_channel_layer):
        """Test consumer handles invalid JSON gracefully."""
        communicator = WebsocketCommunicator(AuctionConsumer.as_asgi(), "/ws/auctions/")
        communicator.scope["user"] = user

        await communicator.connect()

        # Consume initial state
        await communicator.receive_json_from()

        # Send invalid JSON
        await communicator.send_to(text_data="invalid json")

        # Connection should remain open
        # Send valid message to verify
        await communicator.send_json_to({"type": "ping"})
        response = await communicator.receive_json_from()
        assert response["type"] == "pong"

        await communicator.disconnect()
