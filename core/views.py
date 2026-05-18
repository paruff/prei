from __future__ import annotations

import logging
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db.models import Avg, Sum
from django.shortcuts import get_object_or_404, redirect, render

from investor_app.finance.utils import (
    calculate_whatif_monthly_cashflow,
    compute_analysis_for_property,
    score_listing_v1,
)

# keep only the models that are actually used
from core.services.cma import estimate_listing_kpis, find_undervalued, price_per_sqft
from core.services.audit import log_action
from .forms import OperatingExpenseForm, PropertyForm, RentalIncomeForm
from .models import InvestmentAnalysis, Listing, MarketSnapshot, Property, SavedSearch

logger = logging.getLogger(__name__)


def _portfolio_summary(user) -> dict[str, Decimal | int]:
    properties = Property.objects.filter(user=user)
    total_invested = properties.aggregate(total=Sum("purchase_price"))[
        "total"
    ] or Decimal("0")
    average_cap_rate = InvestmentAnalysis.objects.filter(property__user=user).aggregate(
        average=Avg("cap_rate")
    )["average"] or Decimal("0")
    return {
        "total_properties": properties.count(),
        "total_invested": total_invested,
        "average_cap_rate": average_cap_rate,
    }


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect_to_login(request.get_full_path())


@login_required
def dashboard(request):
    properties = (
        Property.objects.filter(user=request.user)
        .select_related("analysis")
        .order_by("-id")
    )

    return render(
        request,
        "dashboard.html",
        {
            "properties": properties,
            "portfolio_summary": _portfolio_summary(request.user),
        },
    )


@login_required
def property_list(request):
    properties = (
        Property.objects.filter(user=request.user)
        .select_related("analysis")
        .order_by("-id")
    )
    return render(
        request,
        "properties/list.html",
        {
            "properties": properties,
            "portfolio_summary": _portfolio_summary(request.user),
        },
    )


@login_required
def property_detail(request, pk: int):
    property_obj = get_object_or_404(
        Property.objects.select_related("analysis"), pk=pk, user=request.user
    )
    return render(
        request,
        "properties/detail.html",
        {
            "property": property_obj,
            "analysis": getattr(property_obj, "analysis", None),
        },
    )


@login_required
def property_add(request):
    if request.method == "POST":
        form = PropertyForm(request.POST)
        if form.is_valid():
            property_obj = form.save(commit=False)
            property_obj.user = request.user
            property_obj.save()
            compute_analysis_for_property(property_obj)
            return redirect("property_add_income", pk=property_obj.pk)
    else:
        form = PropertyForm()

    return render(request, "properties/add.html", {"form": form})


@login_required
def property_edit(request, pk: int):
    property_obj = get_object_or_404(Property, pk=pk, user=request.user)
    if request.method == "POST":
        form = PropertyForm(request.POST, instance=property_obj)
        if form.is_valid():
            property_obj = form.save()
            compute_analysis_for_property(property_obj)
            return redirect("property_detail", pk=property_obj.pk)
    else:
        form = PropertyForm(instance=property_obj)

    return render(
        request,
        "properties/edit.html",
        {
            "form": form,
            "property": property_obj,
        },
    )


@login_required
def property_delete(request, pk: int):
    property_obj = get_object_or_404(Property, pk=pk, user=request.user)
    if request.method == "POST":
        property_obj.delete()
        return redirect("property_list")
    return render(request, "properties/edit.html", {"property": property_obj})


@login_required
def property_add_income(request, pk: int):
    property_obj = get_object_or_404(Property, pk=pk, user=request.user)
    if request.method == "POST":
        form = RentalIncomeForm(request.POST)
        if form.is_valid():
            rental_income = form.save(commit=False)
            rental_income.property = property_obj
            rental_income.save()
            compute_analysis_for_property(property_obj)
            return redirect("property_add_expense", pk=property_obj.pk)
    else:
        form = RentalIncomeForm()
    return render(
        request,
        "income/add.html",
        {
            "form": form,
            "property": property_obj,
        },
    )


@login_required
def property_add_expense(request, pk: int):
    property_obj = get_object_or_404(Property, pk=pk, user=request.user)
    if request.method == "POST":
        form = OperatingExpenseForm(request.POST)
        if form.is_valid():
            operating_expense = form.save(commit=False)
            operating_expense.property = property_obj
            operating_expense.save()
            compute_analysis_for_property(property_obj)
            action = request.POST.get("action")
            if action == "done":
                return redirect("property_detail", pk=property_obj.pk)
            return redirect("property_add_expense", pk=property_obj.pk)
    else:
        form = OperatingExpenseForm()
    return render(
        request,
        "expenses/add.html",
        {
            "form": form,
            "property": property_obj,
        },
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
    # Optionally load a saved search to prefill filters
    saved_id = request.GET.get("saved_id")
    query = request.GET.get("q", "")
    zip_code = request.GET.get("zip", "")
    state = request.GET.get("state", "")
    sort = request.GET.get("sort", "score")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    if saved_id:
        try:
            s = SavedSearch.objects.get(id=int(saved_id), user=request.user)
            query = s.query or query
            zip_code = s.zip_code or zip_code
            state = s.state or state
            # Allow saved bounds to apply unless overridden
            min_price = min_price or (
                str(s.min_price) if s.min_price is not None else None
            )
            max_price = max_price or (
                str(s.max_price) if s.max_price is not None else None
            )
        except (SavedSearch.DoesNotExist, ValueError):
            pass

    qs = Listing.objects.all()
    if query:
        qs = qs.filter(address__icontains=query)
    if zip_code:
        qs = qs.filter(zip_code__iexact=zip_code)
    if state:
        qs = qs.filter(state__iexact=state)

    if min_price:
        try:
            qs = qs.filter(price__gte=min_price)
        except Exception:
            pass
    if max_price:
        try:
            qs = qs.filter(price__lte=max_price)
        except Exception:
            pass

    items = [{"obj": lst, "score": score_listing_v1(lst)} for lst in qs[:200]]
    if sort == "score":
        items.sort(key=lambda x: x["score"], reverse=True)
    elif sort == "price":
        items.sort(key=lambda x: x["obj"].price)

    # Save filter if requested
    if request.method == "POST" and request.user.is_authenticated:
        name = request.POST.get("name") or "Saved Search"
        saved_search = SavedSearch.objects.create(
            user=request.user,
            name=name,
            query=query,
            zip_code=zip_code,
            state=state,
            min_price=request.POST.get("min_price") or None,
            max_price=request.POST.get("max_price") or None,
        )
        log_action(request.user, "saved_search.created", obj=saved_search)

    saved = []
    if request.user.is_authenticated:
        saved = list(
            SavedSearch.objects.filter(user=request.user).order_by("-created_at")[:10]
        )

    return render(
        request,
        "search_listings.html",
        {
            "items": items,
            "q": query,
            "zip": zip_code,
            "state": state,
            "sort": sort,
            "min_price": min_price or "",
            "max_price": max_price or "",
            "saved": saved,
        },
    )


def analyze_property(request, property_id: int):
    from decimal import Decimal

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
    def num(name: str, default: str = "0") -> Decimal:
        try:
            return Decimal(str(request.POST.get(name, default)))
        except Exception:
            return Decimal("0")

    taxes = num("taxes")
    insurance = num("insurance")
    maintenance = num("maintenance")
    management_fees = num("management_fees")
    rehab_estimate = num("rehab_estimate")

    projected_monthly_cash_flow = calculate_whatif_monthly_cashflow(
        annual_noi=analysis.noi,
        taxes=taxes,
        insurance=insurance,
        maintenance=maintenance,
        management_fees=management_fees,
        rehab_estimate=rehab_estimate,
    )

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
        return render(
            request, "property_report.html", {"error": "Listing not found."}, status=404
        )

    score = score_listing_v1(lst)
    ppsf = price_per_sqft(lst)
    market_snapshot = MarketSnapshot.objects.filter(zip_code=lst.zip_code).first()

    try:
        kpis: dict[str, Decimal] = estimate_listing_kpis(lst, market_snapshot)
    except Exception:
        logger.exception(
            "report_listing: KPI computation failed for listing_id=%s", listing_id
        )
        kpis = {
            "cap_rate": Decimal("0"),
            "cash_on_cash": Decimal("0"),
            "dscr": Decimal("0"),
            "noi": Decimal("0"),
        }

    context = {
        "listing": lst,
        "score": score,
        "ppsf": ppsf,
        "market_snapshot": market_snapshot,
        "kpis": kpis,
        "crime": None,
        "schools": None,
    }
    return render(request, "property_report.html", context)


def report_property(request, property_id: int):
    try:
        prop = Property.objects.get(id=property_id)
    except Property.DoesNotExist:
        return render(
            request,
            "property_report.html",
            {"error": "Property not found."},
            status=404,
        )

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
