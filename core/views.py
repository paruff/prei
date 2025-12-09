from __future__ import annotations

# removed unused Decimal import
from django.shortcuts import render

from investor_app.finance.utils import compute_analysis_for_property, score_listing_v1
from core.integrations.market.comps import get_comps_for_listing
from core.integrations.market.rents import get_rent_estimate_for_listing
from core.integrations.market.crime import get_crime_score
from core.integrations.market.schools import get_school_rating

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
    top_growth = sorted(
        snapshots, key=lambda s: (s.price_trend, s.rent_index), reverse=True
    )[:10]
    # Flag undervalued listings globally as a placeholder
    undervalued = find_undervalued(Listing.objects.all()[:200])
    return render(
        request,
        "growth_areas.html",
        {"top_growth": top_growth, "undervalued": undervalued},
    )


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
    return render(
        request,
        "search_listings.html",
        {"items": items, "q": query, "zip": zip_code, "state": state},
    )


def analyze_property(request, property_id: int):
    try:
        prop = Property.objects.get(id=property_id)
    except Property.DoesNotExist:
        return render(
            request,
            "analyze_property.html",
            {"error": "Property not found."},
            status=404,
        )

    analysis = compute_analysis_for_property(prop)

    # What-if inputs for carry costs and rehab estimate
    def num(name, default=0):
        try:
            return float(request.POST.get(name, default))
        except Exception:
            return default

    taxes = num("taxes")
    insurance = num("insurance")
    maintenance = num("maintenance")
    management_fees = num("management_fees")
    rehab_estimate = num("rehab_estimate")

    monthly_income = float(analysis.noi) / 12.0  # NOI approximates net of opex, adjust via inputs
    additional_monthly_costs = taxes + insurance + maintenance + management_fees
    rehab_monthly = rehab_estimate / 12.0 if rehab_estimate else 0.0
    projected_monthly_cash_flow = monthly_income - additional_monthly_costs - rehab_monthly

    carry_costs = {
        "taxes": taxes,
        "insurance": insurance,
        "maintenance": maintenance,
        "management_fees": management_fees,
        "rehab_estimate": rehab_estimate,
        "projected_monthly_cash_flow": projected_monthly_cash_flow,
    }

    return render(
        request,
        "analyze_property.html",
        {"property": prop, "analysis": analysis, "carry_costs": carry_costs},
    )


def report_listing(request, listing_id: int):
    try:
        lst = Listing.objects.get(id=listing_id)
    except Listing.DoesNotExist:
        return render(request, "property_report.html", {"error": "Listing not found."}, status=404)

    comps = get_comps_for_listing(lst)
    rent_estimate = get_rent_estimate_for_listing(lst)
    crime = get_crime_score(lst.zip_code, lst.city, lst.state)
    schools = get_school_rating(lst.zip_code, lst.city, lst.state)
    context = {
        "listing": lst,
        "comps": comps,
        "rent_estimate": rent_estimate,
        "crime": crime,
        "schools": schools,
    }
    return render(request, "property_report.html", context)


def report_property(request, property_id: int):
    try:
        prop = Property.objects.get(id=property_id)
    except Property.DoesNotExist:
        return render(request, "property_report.html", {"error": "Property not found."}, status=404)

    analysis = compute_analysis_for_property(prop)
    context = {
        "property": prop,
        "analysis": analysis,
        "comps": [],
        "rent_estimate": None,
        "crime": None,
        "schools": None,
    }
    return render(request, "property_report.html", context)
