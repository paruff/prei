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
]
