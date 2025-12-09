from __future__ import annotations

# removed unused Decimal import
from django.shortcuts import render

from investor_app.finance.utils import compute_analysis_for_property, score_listing_v1

# keep only the models that are actually used
from .models import InvestmentAnalysis, Listing, Property, MarketSnapshot
from core.services.cma import find_undervalued


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


def growth_areas(request):
    # Simple mock analytics: top MarketSnapshots by price_trend and rent_index
    snapshots = MarketSnapshot.objects.all()[:50]
    top_growth = sorted(snapshots, key=lambda s: (s.price_trend, s.rent_index), reverse=True)[:10]
    # Flag undervalued listings globally as a placeholder
    undervalued = find_undervalued(Listing.objects.all()[:200])
    return render(request, "growth_areas.html", {"top_growth": top_growth, "undervalued": undervalued})


def search_listings(request):
    query = request.GET.get("q", "")
    zip_code = request.GET.get("zip", "")
    state = request.GET.get("state", "")

    qs = Listing.objects.all()
    if query:
        qs = qs.filter(address__icontains=query)
    if zip_code:
        qs = qs.filter(zip_code__iexact=zip_code)
    if state:
        qs = qs.filter(state__iexact=state)

    items = [{"obj": lst, "score": score_listing_v1(lst)} for lst in qs[:100]]
    return render(request, "search_listings.html", {"items": items, "q": query, "zip": zip_code, "state": state})


def analyze_property(request, property_id: int):
    try:
        prop = Property.objects.get(id=property_id)
    except Property.DoesNotExist:
        return render(request, "analyze_property.html", {"error": "Property not found."}, status=404)

    analysis = compute_analysis_for_property(prop)

    # Carry cost sheet placeholders: taxes, insurance, maintenance, mgmt fees
    carry_costs = {
        "taxes": 0,
        "insurance": 0,
        "maintenance": 0,
        "management_fees": 0,
    }

    return render(
        request,
        "analyze_property.html",
        {"property": prop, "analysis": analysis, "carry_costs": carry_costs},
    )
