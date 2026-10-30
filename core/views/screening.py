from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseNotAllowed,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.decorators import is_rate_limited, rate_limit
from core.models import (
    GrowthArea,
)
from .constants import US_STATES


@login_required
def pipeline_screener(request: HttpRequest) -> HttpResponse:
    """Market-centric screening view.

    Shows PipelineProperty records for a growth area with pass/fail
    screening results, sorted by screening result then source type.

    GET params:
      growth_area_id: filter to a specific growth area (required for
                      market-centric view, optional for all-markets view)
      status: ACTIVE (default), KILLED, ON_HOLD
      passed: 1 = passed only, 0 = failed only, blank = all
    """
    from core.models import (
        PipelineProperty,
        ScreeningCriteria,
    )
    from core.services.pipeline import get_source_record
    from core.services.screening import screen_property

    # --- Resolve growth area filter ---
    ga_id = request.GET.get("growth_area_id", "")
    growth_area = None
    if ga_id:
        growth_area = get_object_or_404(GrowthArea, pk=ga_id)

    # --- Filter params ---
    status_filter = request.GET.get("status", "ACTIVE")
    passed_filter = request.GET.get("passed", "")

    # --- Base queryset ---
    qs = (
        PipelineProperty.objects.filter(user=request.user)
        .select_related("growth_area", "investment_analysis")
        .order_by("-screening_passed", "-created_at")
    )

    if growth_area:
        qs = qs.filter(growth_area=growth_area)

    if status_filter:
        qs = qs.filter(status=status_filter)

    if passed_filter == "1":
        qs = qs.filter(screening_passed=True)
    elif passed_filter == "0":
        qs = qs.filter(screening_passed=False)

    # --- Price / rent / cap rate filters ---
    price_min = request.GET.get("price_min", "")
    price_max = request.GET.get("price_max", "")
    rent_min = request.GET.get("rent_min", "")
    cap_rate_min = request.GET.get("cap_rate_min", "")

    if price_min:
        qs = qs.filter(purchase_price__gte=price_min)
    if price_max:
        qs = qs.filter(purchase_price__lte=price_max)
    if rent_min:
        qs = qs.filter(monthly_rent__gte=rent_min)
    if cap_rate_min:
        qs = qs.filter(investment_analysis__cap_rate__gte=Decimal(cap_rate_min) / 100)

    # --- Sort ---
    sort = request.GET.get("sort", "")
    order = request.GET.get("order", "asc")
    SORT_MAP = {
        "price": "purchase_price",
        "rent": "monthly_rent",
        "cap_rate": "investment_analysis__cap_rate",
        "score": "screening_passed",
    }
    if sort in SORT_MAP:
        dir_prefix = "-" if order == "desc" else ""
        qs = qs.order_by(dir_prefix + SORT_MAP[sort])

    # --- Get or create screening criteria ---
    try:
        criteria = ScreeningCriteria.objects.get(user=request.user)
    except ScreeningCriteria.DoesNotExist:
        criteria = None

    # --- Re-screen if user POSTs "rescreen" action ---
    if request.method == "POST" and request.POST.get("action") == "rescreen":
        if is_rate_limited(request, "rescreen", limit=5, window_seconds=300):
            messages.error(
                request,
                "Too many re-screens — please wait a few minutes and try again.",
            )
            return redirect(request.get_full_path())
        if criteria:
            # Use unfiltered queryset — rescreen ALL user properties,
            # not just the growth-area-filtered subset shown on screen
            all_qs = PipelineProperty.objects.filter(user=request.user)
            rescreened = 0
            for pp in all_qs:
                source_record = get_source_record(pp)
                result = screen_property(pp, criteria, source_record=source_record)
                pp.screening_passed = result.passed
                pp.save(update_fields=["screening_passed", "updated_at"])
                rescreened += 1
            messages.success(
                request,
                f"{rescreened} propert{'y' if rescreened == 1 else 'ies'} re-screened.",
            )
            return redirect(request.get_full_path())

    # --- Advance to underwriting action ---
    if request.method == "POST" and request.POST.get("action") == "advance":
        pp_id = request.POST.get("property_id")
        try:
            pp = PipelineProperty.objects.get(pk=pp_id, user=request.user)
            pp.stage = PipelineProperty.Stage.UNDERWRITING
            pp.underwriting_at = timezone.now()
            pp.save(update_fields=["stage", "underwriting_at", "updated_at"])
            messages.success(request, f"{pp.address[:40]} moved to Underwriting.")
        except PipelineProperty.DoesNotExist:
            pass
        return redirect(request.get_full_path())

    # --- Kill action ---
    if request.method == "POST" and request.POST.get("action") == "kill":
        pp_id = request.POST.get("property_id")
        kill_reason = request.POST.get("kill_reason", "Failed screening review")
        try:
            pp = PipelineProperty.objects.get(pk=pp_id, user=request.user)
            pp.status = PipelineProperty.Status.KILLED
            pp.kill_reason = kill_reason
            pp.save(update_fields=["status", "kill_reason", "updated_at"])
        except PipelineProperty.DoesNotExist:
            pass
        return redirect(request.get_full_path())

    # --- Summary counts ---
    total = qs.count()
    passed_count = qs.filter(screening_passed=True).count()
    failed_count = qs.filter(screening_passed=False).count()
    unscreened_count = qs.filter(screening_passed__isnull=True).count()
    passed_pct = (passed_count / total * 100) if total > 0 else 0

    # --- All growth areas for the filter dropdown ---
    user_growth_areas = (
        GrowthArea.objects.filter(pipeline_properties__user=request.user)
        .distinct()
        .order_by("state", "city_name")
    )

    return render(
        request,
        "pipeline/screener.html",
        {
            "growth_area": growth_area,
            "properties": qs,
            "criteria": criteria,
            "total": total,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "unscreened_count": unscreened_count,
            "passed_pct": passed_pct,
            "status_filter": status_filter,
            "passed_filter": passed_filter,
            "user_growth_areas": user_growth_areas,
            "ga_id": ga_id,
        },
    )


@login_required
def screener_filter(request: HttpRequest) -> HttpResponse:
    """Filter screener results via AJAX. Returns HTML fragment."""
    from core.models import PipelineProperty

    qs = PipelineProperty.objects.filter(
        user=request.user,
        stage__in=["DISCOVERED", "SCREENING"],
    )

    # Apply filters from query params
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    min_yield = request.GET.get("min_yield")
    max_ptr = request.GET.get("max_ptr")
    min_beds = request.GET.get("min_beds")
    state = request.GET.get("state")
    prop_type = request.GET.get("prop_type")

    if min_price:
        qs = qs.filter(price__gte=Decimal(min_price))
    if max_price:
        qs = qs.filter(price__lte=Decimal(max_price))
    if min_yield:
        qs = qs.filter(gross_yield_pct__gte=Decimal(min_yield))
    if max_ptr:
        qs = qs.filter(price_to_rent_ratio__lte=Decimal(max_ptr))
    if min_beds:
        qs = qs.filter(beds__gte=int(min_beds))
    if state:
        qs = qs.filter(state=state)
    if prop_type:
        qs = qs.filter(property_type=prop_type)

    return render(
        request,
        "pipeline/screener_results_fragment.html",
        {"properties": qs[:50]},
    )


@login_required
def pipeline_screening_settings(request: HttpRequest) -> HttpResponse:
    """View and edit the user's pipeline screening criteria.

    GET:  loads or creates ScreeningCriteria for the user.
    POST: validates and saves criteria, then re-screens all active
          pipeline properties at DISCOVERED or SCREENING stage.
    """
    from core.models import PipelineProperty, ScreeningCriteria
    from core.services.screening import screen_property

    criteria, _ = ScreeningCriteria.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # Parse form fields
        # Price range
        min_price = request.POST.get("min_price")
        max_price = request.POST.get("max_price")
        if min_price:
            criteria.min_price = Decimal(min_price)
        else:
            criteria.min_price = None
        if max_price:
            criteria.max_price = Decimal(max_price)
        else:
            criteria.max_price = None

        # Yield and ratio (model has default=7.00, NOT NULL — can't be None)
        min_yield = request.POST.get("min_gross_yield_pct", "").strip()
        if min_yield:
            criteria.min_gross_yield_pct = Decimal(min_yield)
        # else: keep existing/default value
        max_ptr = request.POST.get("max_price_to_rent_ratio", "").strip()
        if max_ptr:
            criteria.max_price_to_rent_ratio = Decimal(max_ptr)
        # else: keep existing/default value

        # Beds and size
        min_beds = request.POST.get("min_beds")
        max_beds = request.POST.get("max_beds")
        min_sqft = request.POST.get("min_sqft")
        max_year_built = request.POST.get("max_year_built")
        criteria.min_beds = int(min_beds) if min_beds else 1
        criteria.max_beds = int(max_beds) if max_beds else None
        criteria.min_sqft = int(min_sqft) if min_sqft else None
        criteria.max_year_built = int(max_year_built) if max_year_built else None

        # Allowed values (checkboxes → JSON list)
        criteria.allowed_property_types = request.POST.getlist("allowed_property_types")
        criteria.allowed_states = request.POST.getlist("allowed_states")
        criteria.allowed_foreclosure_statuses = request.POST.getlist(
            "allowed_foreclosure_statuses"
        )

        # GACS score
        min_gacs = request.POST.get("min_gacs_score")
        if min_gacs:
            criteria.min_gacs_score = Decimal(min_gacs)
        else:
            criteria.min_gacs_score = None

        criteria.save()

        # Create version snapshot
        from core.models import ScreeningCriteriaVersion

        ScreeningCriteriaVersion.objects.create(
            criteria=criteria,
            snapshot={
                "min_price": str(criteria.min_price) if criteria.min_price else None,
                "max_price": str(criteria.max_price) if criteria.max_price else None,
                "min_gross_yield_pct": str(criteria.min_gross_yield_pct)
                if criteria.min_gross_yield_pct
                else None,
                "max_price_to_rent_ratio": str(criteria.max_price_to_rent_ratio)
                if criteria.max_price_to_rent_ratio
                else None,
                "min_beds": criteria.min_beds,
                "max_beds": criteria.max_beds,
                "min_sqft": criteria.min_sqft,
                "max_year_built": criteria.max_year_built,
                "allowed_property_types": criteria.allowed_property_types,
                "allowed_states": criteria.allowed_states,
                "min_gacs_score": str(criteria.min_gacs_score)
                if criteria.min_gacs_score
                else None,
            },
        )

        # Re-screen all ACTIVE pipeline properties at DISCOVERED or SCREENING
        rescreen_count = 0
        rescreen_limited = is_rate_limited(
            request, "rescreen_settings", limit=5, window_seconds=300
        )
        if not rescreen_limited:
            for pp in PipelineProperty.objects.filter(
                user=request.user,
                status=PipelineProperty.Status.ACTIVE,
                stage__in=[
                    PipelineProperty.Stage.DISCOVERED,
                    PipelineProperty.Stage.SCREENING,
                ],
            ):
                source_record = None  # Re-resolve source for accurate screening
                from core.services.pipeline import get_source_record

                source_record = get_source_record(pp)
                result = screen_property(pp, criteria, source_record=source_record)
                pp.screening_passed = result.passed
                pp.save(update_fields=["screening_passed", "updated_at"])
                rescreen_count += 1

        if rescreen_limited:
            messages.warning(
                request,
                "Screening criteria saved, but re-screening was skipped "
                "(too many re-screens recently — try again in a few minutes).",
            )
        messages.success(
            request,
            f"Screening criteria saved. {rescreen_count} property(ies) re-screened.",
        )
        return redirect("pipeline_screening_settings")

    return render(
        request,
        "pipeline/screening_settings.html",
        {
            "criteria": criteria,
            "versions": criteria.versions.all()[:5],
            "US_STATES": US_STATES,
            "property_type_choices": [
                "single-family",
                "duplex",
                "triplex",
                "fourplex",
            ],
            "foreclosure_status_choices": [
                "preforeclosure",
                "auction",
                "reo",
                "government",
            ],
        },
    )


@login_required
@rate_limit("screening_preview", limit=10, window_seconds=300)
def screening_preview(request: HttpRequest) -> HttpResponse:
    """Preview how many properties pass current criteria without saving.

    Uses the actual screen_property function for accuracy.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    from core.models import PipelineProperty, ScreeningCriteria
    from core.services.pipeline import get_source_record
    from core.services.screening import screen_property

    criteria, _ = ScreeningCriteria.objects.get_or_create(user=request.user)
    properties = PipelineProperty.objects.filter(
        user=request.user,
        stage__in=["DISCOVERED", "SCREENING"],
    )

    total = properties.count()
    passed = 0

    for pp in properties:
        source_record = get_source_record(pp)
        result = screen_property(
            pp, criteria, source_record=source_record, cache_rent=False
        )
        if result.passed:
            passed += 1

    killed = total - passed

    return JsonResponse({"total": total, "passed": passed, "killed": killed})
