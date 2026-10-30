from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import (
    HttpRequest,
    HttpResponse,
)
from django.shortcuts import redirect, render

from core.integrations.market.market_trends import get_market_health_summary
from core.models import (
    GrowthArea,
    PipelineAsset,
    Property,
    UserInvestmentTargets,
)

from .permissions import _is_client_only_user
from .constants import US_STATES


@login_required
def dashboard(request):
    if _is_client_only_user(request.user):
        return redirect("property_list")

    from core.services.scoring import score_listing_v2

    try:
        targets = UserInvestmentTargets.objects.get(user=request.user)
    except UserInvestmentTargets.DoesNotExist:
        targets = None

    properties_qs = (
        Property.objects.filter(
            Q(user=request.user) | Q(property_shares__shared_with=request.user)
        )
        .select_related("analysis")
        .distinct()
        .order_by("-id")
    )

    VERDICT_MAP = {
        "Strong Buy": ("A", "Strong Buy"),
        "Conditional": ("B", "Conditional"),
        "Pass": ("C", "Pass"),
    }

    properties: list[dict] = []
    for prop in properties_qs:
        if (
            targets is None
            or prop.monthly_rent_gross is None
            or prop.monthly_rent_gross <= 0
            or prop.purchase_price is None
            or prop.purchase_price <= 0
        ):
            continue

        try:
            score = score_listing_v2(prop, targets)
        except Exception:
            continue

        verdict_code, verdict_label = VERDICT_MAP.get(score.verdict, ("C", "Pass"))

        properties.append(
            {
                "id": prop.id,
                "address": prop.address,
                "city": prop.city,
                "state": prop.state,
                "property_type": prop.get_property_type_display(),
                "score": score.total_score,
                "verdict": verdict_code,
                "verdict_label": verdict_label,
                "coc": score.cash_on_cash,
                "cap_rate": score.cap_rate,
                "dscr": score.dscr,
                "grm": score.grm,
                "passes_one_pct": score.passes_one_pct_rule,
            }
        )

    # Sort by score descending — best deals first
    properties.sort(key=lambda p: p["score"], reverse=True)

    # Compute summary
    coc_values = [p["coc"] for p in properties if p["coc"] is not None]
    dscr_values = [p["dscr"] for p in properties if p["dscr"] is not None]

    passes_one_pct_count = sum(1 for p in properties if p["passes_one_pct"])

    summary = {
        "total_count": len(properties),
        "strong_buy_count": sum(1 for p in properties if p["verdict"] == "A"),
        "passes_one_pct_count": passes_one_pct_count,
        "passes_one_pct_display": (f"{passes_one_pct_count} / {len(properties)}"),
        "best_coc": max(coc_values) if coc_values else Decimal("0"),
        "avg_dscr": (
            sum(dscr_values) / len(dscr_values) if dscr_values else Decimal("0")
        ),
        "total_equity": int(
            sum(p["price"] for p in properties if p.get("price"))
            / max(sum(1 for _ in properties), 1)
        ),
    }

    return render(
        request,
        "dashboard.html",
        {
            "properties": properties,
            "summary": summary,
        },
    )


@login_required
def onboard(request: HttpRequest) -> HttpResponse:
    """Onboarding wizard — first-login setup for API keys and preferences."""
    from core.models import ScreeningCriteria, UserProfile

    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile.is_onboarded = True
        profile.save(update_fields=["is_onboarded"])

        criteria, _ = ScreeningCriteria.objects.get_or_create(user=request.user)
        state = request.POST.get("target_state", "").strip().upper()
        if state:
            criteria.allowed_states = [state]
        min_price = request.POST.get("min_price", "").strip()
        if min_price:
            try:
                criteria.min_price = Decimal(min_price)
            except Exception:
                pass
        max_price = request.POST.get("max_price", "").strip()
        if max_price:
            try:
                criteria.max_price = Decimal(max_price)
            except Exception:
                pass
        criteria.save()

        messages.success(request, "Setup complete! Here's your dashboard.")
        return redirect("dashboard")

    return render(request, "onboard.html", {"profile": profile, "states": US_STATES})


def pipeline_dashboard(request: HttpRequest) -> HttpResponse:
    """Pipeline dashboard showing stage distribution and screening results.

    Queries the PipelineAsset Django model for persisted pipeline state.
    Each row links back to the growth explorer or pipeline detail.
    """
    from collections import Counter

    # Query all pipeline-tracked assets
    assets = PipelineAsset.objects.all().order_by("-updated_at")

    # Stage distribution (StateAggregator-style)
    stage_counts: dict[str, int] = dict(Counter(a.current_stage for a in assets))
    total = len(assets)

    # Pipeline flow grouping
    flow = {
        "acquisition": sum(
            stage_counts.get(s, 0) for s in ["GACS", "DISCOVERY", "SCREENING"]
        ),
        "deal_making": sum(
            stage_counts.get(s, 0)
            for s in ["UNDERWRITING", "OFFER", "DUE_DILIGENCE", "CLOSING"]
        ),
        "operations": sum(stage_counts.get(s, 0) for s in ["TURNOVER", "LEASING"]),
        "portfolio": stage_counts.get("PORTFOLIO", 0),
    }

    # Screening results table (killed = screening failure, advanced = passed)
    # Show the 50 most recent, split by killed vs advanced
    killed = assets.filter(current_stage="KILLED")[:25]
    advanced = assets.exclude(current_stage__in=["KILLED", "GACS"])[:25]

    return render(
        request,
        "pipeline_dashboard.html",
        {
            "total_assets": total,
            "stage_counts": stage_counts,
            "flow": flow,
            "killed_assets": killed,
            "advanced_assets": advanced,
            "all_assets": assets[:50],
        },
    )


@login_required
def portfolio_dashboard(request: HttpRequest) -> HttpResponse:
    """Portfolio dashboard — shows acquired properties and matching growth areas."""
    from core.models import PipelineProperty

    # Get acquired properties
    qs = PipelineProperty.objects.filter(
        user=request.user,
        status=PipelineProperty.Status.ACQUIRED,
    ).order_by("-acquired_at")

    total = qs.count()
    total_equity = sum((p.price or 0) for p in qs)
    total_rent = sum((p.estimated_rent or 0) for p in qs)
    scores = [p.gacs_score for p in qs if p.gacs_score]
    avg_gacs = sum(scores) / len(scores) if scores else 0

    # Show top growth areas
    growth_areas = GrowthArea.objects.filter(composite_score__isnull=False).order_by(
        "-composite_score"
    )[:10]

    return render(
        request,
        "portfolio_dashboard.html",
        {
            "properties": qs,
            "total_properties": total,
            "total_equity": total_equity,
            "total_monthly_cf": total_rent,
            "avg_gacs": avg_gacs,
            "growth_areas": growth_areas,
        },
    )


@login_required
def market_dashboard(request: HttpRequest) -> HttpResponse:
    """Market cycle indicators dashboard — shows key market health metrics by metro area."""
    from core.models.growth import MarketIndicator

    metro_filter = request.GET.get("metro", "").strip()

    metro_qs = (
        MarketIndicator.objects.values("metro_area").distinct().order_by("metro_area")
    )
    if metro_filter:
        metro_qs = metro_qs.filter(metro_area__icontains=metro_filter)

    market_data = []
    for metro in metro_qs:
        metro_name = metro["metro_area"]
        summary = get_market_health_summary(metro_name)
        indicators = summary.get("indicators", {})

        market_data.append(
            {
                "metro_area": metro_name,
                "overall_health": summary.get("overall_health", "caution"),
                "health_counts": summary.get("health_counts", {}),
                "indicators": indicators,
            }
        )

    return render(
        request,
        "markets/dashboard.html",
        {
            "market_data": market_data,
            "metro_filter": metro_filter,
        },
    )


@login_required
def update_market_indicators(request: HttpRequest) -> HttpResponse:
    """Update market indicators from external data sources."""
    from core.integrations.market.market_trends import update_market_indicators

    result = update_market_indicators()
    messages.success(
        request,
        f"Updated {result['created']} new indicators, {result['updated']} updated, {result['errors']} errors",
    )
    return redirect("markets_dashboard")
