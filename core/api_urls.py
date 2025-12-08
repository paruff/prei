from django.urls import path

from . import api_views

app_name = "api"

urlpatterns = [
    path(
        "v1/real-estate/growth-areas",
        api_views.growth_areas_list,
        name="growth-areas-list",
    ),
]
