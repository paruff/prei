from __future__ import annotations

import json
import logging
from typing import Any, Dict

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from .models import ForeclosureProperty, UserWatchlist

User = get_user_model()
logger = logging.getLogger(__name__)


class AuctionConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time auction updates."""

    async def connect(self) -> None:
        """Handle WebSocket connection."""
        self.user = self.scope["user"]

        if not self.user.is_authenticated:  # type: ignore[union-attr]
            await self.close()
            return

        self.user_group_name = f"user_{self.user.id}"  # type: ignore[union-attr]

        # Join user-specific group
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)

        await self.accept()

        # Send initial state
        await self.send_initial_state()

        logger.info(f"WebSocket connected for user {self.user.username}")  # type: ignore[union-attr]

    async def disconnect(self, close_code: int) -> None:
        """Handle WebSocket disconnection."""
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(
                self.user_group_name, self.channel_name
            )
            logger.info(f"WebSocket disconnected for user {self.user.username}")  # type: ignore[union-attr]

    async def receive(self, text_data: str = "") -> None:  # type: ignore[override]
        """Handle messages from WebSocket."""
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "subscribe":
                await self.handle_subscribe(data.get("propertyId"))
            elif message_type == "unsubscribe":
                await self.handle_unsubscribe(data.get("propertyId"))
            elif message_type == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")

    async def send_initial_state(self) -> None:
        """Send current auction states for user's watchlist."""
        auctions = await self.get_user_watchlist_auctions()

        await self.send(
            text_data=json.dumps(
                {
                    "type": "initial_state",
                    "auctions": auctions,
                }
            )
        )

    async def handle_subscribe(self, property_id: str) -> None:
        """Add property to user's watchlist."""
        if not property_id:
            return

        success = await self.add_to_watchlist(property_id)

        await self.send(
            text_data=json.dumps(
                {
                    "type": "subscribe_response",
                    "propertyId": property_id,
                    "success": success,
                }
            )
        )

    async def handle_unsubscribe(self, property_id: str) -> None:
        """Remove property from user's watchlist."""
        if not property_id:
            return

        success = await self.remove_from_watchlist(property_id)

        await self.send(
            text_data=json.dumps(
                {
                    "type": "unsubscribe_response",
                    "propertyId": property_id,
                    "success": success,
                }
            )
        )

    async def auction_update(self, event: Dict[str, Any]) -> None:
        """Handle auction update broadcast from channel layer."""
        await self.send(text_data=json.dumps(event["message"]))

    @database_sync_to_async
    def get_user_watchlist_auctions(self) -> list:
        """Get all auctions in user's watchlist."""
        watchlist_items = UserWatchlist.objects.filter(user=self.user).select_related(  # type: ignore[misc]
            "property"
        )

        auctions = []
        for item in watchlist_items:
            prop = item.property
            auctions.append(
                {
                    "propertyId": str(prop.id),
                    "street": prop.street,
                    "city": prop.city,
                    "state": prop.state,
                    "zipCode": prop.zip_code,
                    "foreclosureStatus": prop.foreclosure_status,
                    "auctionDate": (
                        prop.auction_date.isoformat() if prop.auction_date else None
                    ),
                    "auctionTime": prop.auction_time,
                    "openingBid": float(prop.opening_bid) if prop.opening_bid else None,
                }
            )

        return auctions

    @database_sync_to_async
    def add_to_watchlist(self, property_id: str) -> bool:
        """Add property to user's watchlist."""
        try:
            property_obj = ForeclosureProperty.objects.get(id=property_id)
            UserWatchlist.objects.get_or_create(user=self.user, property=property_obj)
            return True
        except ForeclosureProperty.DoesNotExist:
            logger.error(f"Property {property_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}")
            return False

    @database_sync_to_async
    def remove_from_watchlist(self, property_id: str) -> bool:
        """Remove property from user's watchlist."""
        try:
            # Convert property_id to int for filtering
            UserWatchlist.objects.filter(  # type: ignore[misc]
                user=self.user, property__id=int(property_id)
            ).delete()
            return True
        except Exception as e:
            logger.error(f"Error removing from watchlist: {e}")
            return False
