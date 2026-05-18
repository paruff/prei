from django.urls import path

from . import views
from .views_portfolio import portfolio_dashboard

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("properties/", views.property_list, name="property_list"),
    path("properties/<int:pk>/", views.property_detail, name="property_detail"),
    path("growth/", views.growth_areas, name="growth_areas"),
    path("search/", views.search_listings, name="search_listings"),
    path("analyze/<int:property_id>/", views.analyze_property, name="analyze_property"),
    # Canonical report URL (listing/<id>/report/)
    path(
        "listing/<int:listing_id>/report/",
        views.report_listing,
        name="report_listing",
    ),
    # Legacy URL kept for backward compatibility
    path(
        "report/listing/<int:listing_id>/",
        views.report_listing,
    ),
    path(
        "report/property/<int:property_id>/",
        views.report_property,
        name="report_property",
    ),
    path("portfolio/", portfolio_dashboard, name="portfolio_dashboard"),
]
