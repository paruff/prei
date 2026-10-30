from __future__ import annotations

import io
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import (
    HttpRequest,
    HttpResponse,
)
from django.shortcuts import redirect, render
from django.views import View

from core.forms import (
    InvestmentTargetsForm,
)
from core.models import (
    Property,
    UserInvestmentTargets,
    UserScreeningPreferences,
)


@login_required
def investment_targets_edit(request: HttpRequest) -> HttpResponse:
    """Edit the current user's investment targets and screening preferences."""
    targets, _created = UserInvestmentTargets.objects.get_or_create(user=request.user)
    prefs, _ = UserScreeningPreferences.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = InvestmentTargetsForm(request.POST, instance=targets)
        if form.is_valid():
            form.save()
            # Save screening preferences
            prefs.min_gross_yield = Decimal(request.POST.get("min_gross_yield", "0.07"))
            prefs.max_price_to_rent_ratio = Decimal(
                request.POST.get("max_price_to_rent_ratio", "15.00")
            )
            prefs.min_beds = int(request.POST.get("min_beds", 1))
            prefs.min_baths = int(request.POST.get("min_baths", 1))
            prefs.save()
            return redirect("investment_targets_edit")
    else:
        form = InvestmentTargetsForm(instance=targets)

    return render(
        request,
        "investment_targets/edit.html",
        {"form": form, "targets": targets, "prefs": prefs},
    )


class MarketRefreshView(LoginRequiredMixin, View):
    """Secure market data refresh — only queries the authenticated user's ZIPs."""

    def post(self, request):
        user_zips = list(
            Property.objects.filter(user=request.user)
            .values_list("zip_code", flat=True)
            .distinct()
        )
        from django.core import management

        for zip_code in user_zips:
            management.call_command(
                "refresh_market_data", zip=zip_code, stdout=io.StringIO()
            )
        messages.success(
            request, f"Market data refreshed for {len(user_zips)} ZIP code(s)."
        )
        return redirect("markets_list")

    def get(self, request):
        # GET not allowed — redirect silently
        return redirect("markets_list")


@login_required
def markets_list(request: HttpRequest) -> HttpResponse:
    """List markets (ZIPs) for the authenticated user's properties."""
    from core.services.market_scoring import score_market_by_zip

    # Get distinct ZIP codes that have at least one of the user's properties
    zip_counts = (
        Property.objects.filter(user=request.user)
        .values("zip_code")
        .annotate(property_count=Count("id"))
        .exclude(zip_code="")
        .order_by("zip_code")
    )

    markets = []
    for entry in zip_counts:
        zip_code = entry["zip_code"]
        market_data = score_market_by_zip(zip_code)
        market_data["property_count"] = entry["property_count"]
        # Add MSA name from MarketSnapshot if available
        try:
            from core.models import MarketSnapshot

            snapshot = (
                MarketSnapshot.objects.filter(zip_code=zip_code, area_type="zip")
                .order_by("-fetched_at")
                .first()
            )
            market_data["msa_name"] = snapshot.msa_name if snapshot else ""
        except Exception:
            market_data["msa_name"] = ""
        markets.append(market_data)

    has_market_data = len(markets) > 0

    return render(
        request,
        "markets/list.html",
        {"markets": markets, "has_market_data": has_market_data},
    )


@login_required
def brrrr_calculator(request: HttpRequest) -> HttpResponse:
    """Standalone BRRRR calculator page — no login required.

    Accepts POST with deal inputs and renders the BRRRRAnalysis result.
    GET renders an empty form.
    """
    from decimal import Decimal

    from core.services.brrrr import calculate_brrrr

    result = None
    form_data: dict[str, str] = {}

    if request.method == "POST":
        # Collect form values
        form_data = {
            "purchase_price": request.POST.get("purchase_price", ""),
            "rehab_cost": request.POST.get("rehab_cost", ""),
            "arv": request.POST.get("arv", ""),
            "monthly_rent_post_rehab": request.POST.get("monthly_rent_post_rehab", ""),
            "annual_operating_expenses": request.POST.get(
                "annual_operating_expenses", ""
            ),
            "refi_ltv_pct": request.POST.get("refi_ltv_pct", "75"),
            "refi_interest_rate": request.POST.get("refi_interest_rate", "7"),
            "refi_term_years": request.POST.get("refi_term_years", "30"),
            "closing_costs_pct": request.POST.get("closing_costs_pct", "2"),
        }

        try:
            result = calculate_brrrr(
                purchase_price=Decimal(form_data["purchase_price"]),
                rehab_cost=Decimal(form_data["rehab_cost"]),
                arv=Decimal(form_data["arv"]),
                monthly_rent_post_rehab=Decimal(form_data["monthly_rent_post_rehab"]),
                annual_operating_expenses=Decimal(
                    form_data["annual_operating_expenses"]
                ),
                refi_ltv_pct=Decimal(form_data["refi_ltv_pct"]) / Decimal("100"),
                refi_interest_rate=Decimal(form_data["refi_interest_rate"])
                / Decimal("100"),
                refi_term_years=int(form_data["refi_term_years"]),
                closing_costs_pct=Decimal(form_data["closing_costs_pct"])
                / Decimal("100"),
            )
        except InvalidOperation, ValueError, ZeroDivisionError:
            # Invalid input — render form with no result
            result = None

    return render(
        request,
        "brrrr_calculator.html",
        {"result": result, "form_data": form_data},
    )


@login_required
def sell_index(request: HttpRequest) -> HttpResponse:
    """Sell/Disposition stub page — placeholder for future disposition tools."""
    return render(request, "sell_index.html")
