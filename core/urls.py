from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("growth/", views.growth_areas, name="growth_areas"),
    path("search/", views.search_listings, name="search_listings"),
    path("analyze/<int:property_id>/", views.analyze_property, name="analyze_property"),
    path("report/listing/<int:listing_id>/", views.report_listing, name="report_listing"),
    path("report/property/<int:property_id>/", views.report_property, name="report_property"),
]
