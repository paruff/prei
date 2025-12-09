from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from .models import (
    AuctionAlert,
    ForeclosureProperty,
    Notification,
    NotificationPreference,
    UserWatchlist,
)

logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def monitor_auctions_task() -> None:
    """
    Monitor all active auctions for status changes.
    Runs every 15 minutes via Celery Beat.
    """
    logger.info("Starting auction monitoring task")

    # Get all auctions within next 30 days or recently completed
    cutoff_date = timezone.now() + timedelta(days=30)
    past_cutoff = timezone.now() - timedelta(days=7)

    auctions = ForeclosureProperty.objects.filter(
        Q(auction_date__lte=cutoff_date, auction_date__gte=past_cutoff)
        | Q(foreclosure_status__in=["auction", "preforeclosure"])
    )

    logger.info(f"Monitoring {auctions.count()} auctions")

    for auction in auctions:
        try:
            check_auction_for_changes(auction)
        except Exception as e:
            logger.error(f"Error checking auction {auction.id}: {e}")

    logger.info("Auction monitoring task completed")


def check_auction_for_changes(auction: ForeclosureProperty) -> None:
    """Check individual auction for changes and broadcast if needed."""
    # In a real implementation, this would fetch latest data from external source
    # For now, we'll detect changes by comparing with a cached version

    # Get users watching this property
    watchers = UserWatchlist.objects.filter(property=auction).select_related("user")

    if not watchers.exists():
        return  # No one watching, skip

    # Here you would:
    # 1. Fetch latest data from external source
    # 2. Compare with current database state
    # 3. If changes detected, broadcast and notify

    # Example: Detect if auction date is approaching
    if auction.auction_date:
        days_until_auction = (auction.auction_date - timezone.now().date()).days

        if days_until_auction in [7, 3, 1]:
            # Send reminder
            for watcher in watchers:
                send_auction_reminder_notification(
                    watcher.user, auction, days_until_auction
                )


def broadcast_auction_update(property_id: int, changes: Dict[str, Any]) -> None:
    """Broadcast auction update to all subscribed users via WebSocket."""
    channel_layer = get_channel_layer()

    # Get users watching this property
    watchers = UserWatchlist.objects.filter(property_id=property_id).values_list(
        "user_id", flat=True
    )

    message = {
        "type": "auction_update",
        "propertyId": str(property_id),
        "update": changes,
        "timestamp": timezone.now().isoformat(),
    }

    # Send to each user's group
    for user_id in watchers:
        user_group = f"user_{user_id}"
        async_to_sync(channel_layer.group_send)(  # type: ignore[union-attr]
            user_group,
            {
                "type": "auction.update",
                "message": message,
            },
        )

    logger.info(
        f"Broadcast auction update for property {property_id} to {watchers.count()} users"
    )


@shared_task(ignore_result=True)
def send_auction_reminders() -> None:
    """
    Send reminders for upcoming auctions.
    Runs every 30 minutes via Celery Beat.
    """
    logger.info("Starting auction reminders task")

    now = timezone.now()

    # Define reminder windows (7 days, 3 days, 1 day, 1 hour)
    reminder_windows = [
        (timedelta(days=7), timedelta(days=7, hours=1)),
        (timedelta(days=3), timedelta(days=3, hours=1)),
        (timedelta(days=1), timedelta(days=1, hours=1)),
        (timedelta(hours=1), timedelta(hours=1, minutes=30)),
    ]

    for window_start, window_end in reminder_windows:
        auction_date_start = now + window_start
        auction_date_end = now + window_end

        auctions = ForeclosureProperty.objects.filter(
            auction_date__gte=auction_date_start.date(),
            auction_date__lte=auction_date_end.date(),
            foreclosure_status__in=["auction", "preforeclosure"],
        )

        for auction in auctions:
            watchers = UserWatchlist.objects.filter(property=auction).select_related(
                "user"
            )

            for watcher in watchers:
                days_until = window_start.days
                if days_until == 0:
                    hours_until = window_start.total_seconds() / 3600
                    send_auction_reminder_notification(
                        watcher.user, auction, hours=int(hours_until)
                    )
                else:
                    send_auction_reminder_notification(
                        watcher.user, auction, days_until
                    )

    logger.info("Auction reminders task completed")


def send_auction_reminder_notification(
    user, auction: ForeclosureProperty, days: int = 0, hours: int = 0
) -> None:
    """Send auction reminder notification to a user."""
    # Check notification preferences
    try:
        prefs = NotificationPreference.objects.get(user=user)
        if prefs.is_quiet_hours():
            logger.info(f"Skipping notification for {user.username} during quiet hours")
            return
    except NotificationPreference.DoesNotExist:
        prefs = None

    # Create notification
    if days > 0:
        title = f"Auction in {days} day{'s' if days > 1 else ''}"
        body = f"{auction.street}, {auction.city}, {auction.state} auction is in {days} day{'s' if days > 1 else ''}"
    else:
        title = f"Auction in {hours} hour{'s' if hours > 1 else ''}"
        body = f"{auction.street}, {auction.city}, {auction.state} auction is in {hours} hour{'s' if hours > 1 else ''}"

    notification = Notification.objects.create(
        user=user,
        notification_type="reminder",
        priority="high" if (days <= 1 or hours <= 24) else "medium",
        title=title,
        body=body,
        property=auction,
        url=f"/foreclosures/{auction.id}/",
        data={
            "days_until": days,
            "hours_until": hours,
            "auction_date": (
                auction.auction_date.isoformat() if auction.auction_date else None
            ),
        },
    )

    # Broadcast via WebSocket
    channel_layer = get_channel_layer()
    user_group = f"user_{user.id}"

    async_to_sync(channel_layer.group_send)(  # type: ignore[union-attr]
        user_group,
        {
            "type": "auction.update",
            "message": {
                "type": "reminder",
                "propertyId": str(auction.id),
                "notification": {
                    "id": notification.id,
                    "title": title,
                    "body": body,
                    "priority": notification.priority,
                },
                "timestamp": timezone.now().isoformat(),
            },
        },
    )

    logger.info(
        f"Sent reminder notification to {user.username} for property {auction.id}"
    )


@shared_task(ignore_result=True)
def check_new_auctions_for_alerts() -> None:
    """
    Check newly added/updated auctions against user alert criteria.
    """
    logger.info("Checking new auctions for alerts")

    # Get recently updated auctions (last 30 minutes)
    cutoff_time = timezone.now() - timedelta(minutes=30)
    recent_auctions = ForeclosureProperty.objects.filter(updated_at__gte=cutoff_time)

    logger.info(f"Found {recent_auctions.count()} recently updated auctions")

    # Get all active alerts
    active_alerts = AuctionAlert.objects.filter(is_active=True).select_related("user")

    for alert in active_alerts:
        for auction in recent_auctions:
            if alert.matches_property(auction):
                send_alert_notification(alert.user, auction, alert)


def send_alert_notification(
    user, auction: ForeclosureProperty, alert: AuctionAlert
) -> None:
    """Send notification for alert match."""
    notification = Notification.objects.create(
        user=user,
        notification_type="auction_update",
        priority="medium",
        title=f"New auction matches '{alert.name}'",
        body=f"{auction.street}, {auction.city}, {auction.state}",
        property=auction,
        url=f"/foreclosures/{auction.id}/",
        data={"alert_id": alert.id, "alert_name": alert.name},
    )

    # Broadcast via WebSocket
    channel_layer = get_channel_layer()
    user_group = f"user_{user.id}"

    async_to_sync(channel_layer.group_send)(  # type: ignore[union-attr]
        user_group,
        {
            "type": "auction.update",
            "message": {
                "type": "alert_match",
                "propertyId": str(auction.id),
                "notification": {
                    "id": notification.id,
                    "title": notification.title,
                    "body": notification.body,
                    "priority": notification.priority,
                },
                "timestamp": timezone.now().isoformat(),
            },
        },
    )

    logger.info(f"Sent alert notification to {user.username} for alert '{alert.name}'")
