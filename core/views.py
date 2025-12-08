from __future__ import annotations

# removed unused Decimal import
from django.shortcuts import render

from investor_app.finance.utils import compute_analysis_for_property, score_listing_v1

# keep only the models that are actually used
from .models import InvestmentAnalysis, Listing, Property


def dashboard(request):
    # Property analyses (existing)
    properties = Property.objects.all()[:20]
    analyses: list[InvestmentAnalysis] = []
    for p in properties:
        analysis = compute_analysis_for_property(p)
        analyses.append(analysis)

    # Basic listing filters
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    state = request.GET.get("state")

    listings_qs = Listing.objects.all()
    if min_price:
        listings_qs = listings_qs.filter(price__gte=min_price)
    if max_price:
        listings_qs = listings_qs.filter(price__lte=max_price)
    if state:
        listings_qs = listings_qs.filter(state__iexact=state)

    listings = []
    for lst in listings_qs[:50]:
        listings.append(
            {
                "obj": lst,
                "score": score_listing_v1(lst),
            }
        )

    return render(
        request,
        "dashboard.html",
        {"analyses": analyses, "listings": listings},
    )
