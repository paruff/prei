from django.urls import path

from . import api_views

app_name = "api"

urlpatterns = [
    path(
        "v1/real-estate/growth-areas",
        api_views.growth_areas_list,
        name="growth-areas-list",
    ),
    path(
        "v1/foreclosures",
        api_views.foreclosures_list,
        name="foreclosures-list",
    ),
    path(
        "v1/real-estate/carrying-costs/calculate",
        api_views.calculate_carrying_costs,
        name="carrying-costs-calculate",
    ),
    # Watchlist endpoints
    path(
        "v1/watchlist",
        api_views.watchlist_view,
        name="watchlist",
    ),
    path(
        "v1/watchlist/<int:item_id>",
        api_views.watchlist_item_delete,
        name="watchlist-item-delete",
    ),
    # Alert endpoints
    path(
        "v1/alerts",
        api_views.alerts_view,
        name="alerts",
    ),
    path(
        "v1/alerts/<int:alert_id>",
        api_views.alert_detail,
        name="alert-detail",
    ),
    # Notification endpoints
    path(
        "v1/notifications",
        api_views.notifications_view,
        name="notifications",
    ),
    path(
        "v1/notifications/<int:notification_id>/read",
        api_views.notification_mark_read,
        name="notification-mark-read",
    ),
    path(
        "v1/notifications/<int:notification_id>/dismiss",
        api_views.notification_dismiss,
        name="notification-dismiss",
    ),
    # Notification preferences endpoint
    path(
        "v1/notification-preferences",
        api_views.notification_preferences_view,
        name="notification-preferences",
    ),
]
