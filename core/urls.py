from django.urls import path

from . import views
from .views_portfolio import portfolio_dashboard

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health_check, name="health_check"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("properties/add/", views.property_add, name="property_add"),
    path("properties/", views.property_list, name="property_list"),
    path("properties/compare/", views.property_compare, name="property_compare"),
    path("properties/<int:pk>/edit/", views.property_edit, name="property_edit"),
    path("properties/<int:pk>/delete/", views.property_delete, name="property_delete"),
    path("properties/<int:pk>/share/", views.property_share, name="property_share"),
    path(
        "properties/<int:pk>/export/pdf/", views.export_pdf, name="property_export_pdf"
    ),
    path("properties/<int:pk>/", views.property_detail, name="property_detail"),
    path(
        "properties/<int:pk>/add-income/",
        views.property_add_income,
        name="property_add_income",
    ),
    path(
        "properties/<int:pk>/add-expense/",
        views.property_add_expense,
        name="property_add_expense",
    ),
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
