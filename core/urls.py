from django.urls import path

from . import views
from .views import MarketRefreshView
from .views_portfolio import portfolio_actuals_add, portfolio_dashboard

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health_check, name="health_check"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("properties/add/", views.property_add, name="property_add"),
    path("properties/create/", views.property_add, name="property_create"),
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
    path(
        "growth/export/csv/",
        views.growth_areas_export_csv,
        name="growth_areas_export_csv",
    ),
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
    path("portfolio/actuals/add/", portfolio_actuals_add, name="portfolio_actuals_add"),
    path("vrm-properties/", views.vrm_properties_list, name="vrm_properties_list"),
    path("growth-explorer/", views.growth_explorer, name="growth_explorer"),
    path("pipeline/", views.pipeline_dashboard, name="pipeline_dashboard"),
    path("pipeline/list/", views.pipeline_list, name="pipeline_list"),
    path("pipeline/<int:pk>/", views.pipeline_detail, name="pipeline_detail"),
    path(
        "pipeline/add-from-source/",
        views.pipeline_add_from_source,
        name="pipeline_add_from_source",
    ),
    path(
        "pipeline/screening/settings/",
        views.pipeline_screening_settings,
        name="pipeline_screening_settings",
    ),
    path(
        "settings/investment-targets/",
        views.investment_targets_edit,
        name="investment_targets_edit",
    ),
    path("markets/", views.markets_list, name="markets_list"),
    path("markets/refresh/", MarketRefreshView.as_view(), name="market_refresh"),
    path("brrrr/", views.brrrr_calculator, name="brrrr_calculator"),
    path("sell/", views.sell_index, name="sell_index"),
]
