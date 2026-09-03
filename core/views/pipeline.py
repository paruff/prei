from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseNotAllowed,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from core.models import (
    GrowthArea,
    HudProperty,
    UsdaProperty,
    VrmProperty,
)


@login_required
def pipeline_list(request: HttpRequest) -> HttpResponse:
    """Pipeline property list with stage funnel and filtering.

    GET params:
      status: filter by status (ACTIVE, KILLED, ON_HOLD) — default ACTIVE
      stage:  filter by stage (SCREENING, UNDERWRITING, etc) — optional
      month:  set to 'this' to filter to current month's properties
      source: filter by source_type (vrm, hud, usda, etc) — optional
      q:      search term — filters by address or source_id (case-insensitive)
    """
    from django.utils import timezone as tz

    from core.models import PipelineProperty

    status_filter = request.GET.get("status", "ACTIVE")
    stage_filter = request.GET.get("stage", "")
    month_filter = request.GET.get("month", "")
    source_filter = request.GET.get("source", "")
    search_term = request.GET.get("q", "").strip()

    qs = (
        PipelineProperty.objects.filter(user=request.user)
        .select_related("investment_analysis", "property_record")
        .order_by("-updated_at")
    )

    if status_filter:
        qs = qs.filter(status=status_filter)
    if stage_filter:
        qs = qs.filter(stage=stage_filter)
    if month_filter == "this":
        now = tz.now()
        qs = qs.filter(created_at__month=now.month, created_at__year=now.year)
    if source_filter:
        qs = qs.filter(source_type=source_filter)
    if search_term:
        qs = qs.filter(
            Q(address__icontains=search_term) | Q(source_id__icontains=search_term)
        )

    # Stage counts for funnel header
    stage_qs = PipelineProperty.objects.filter(user=request.user)
    if month_filter == "this":
        now = tz.now()
        stage_qs = stage_qs.filter(
            created_at__month=now.month, created_at__year=now.year
        )
    if source_filter:
        stage_qs = stage_qs.filter(source_type=source_filter)
    stage_counts: dict[str, int] = dict(
        stage_qs.values("stage")
        .annotate(count=Count("id"))
        .values_list("stage", "count")
    )

    # Build ordered list of (stage_label, count) for template display
    stage_order = [
        "DISCOVERED",
        "SCREENING",
        "UNDERWRITING",
        "OFFER",
        "DUE_DILIGENCE",
        "CLOSING",
        "ACQUIRED",
        "RENOVATION",
        "STABILIZED",
    ]
    stage_items = [(s, stage_counts.get(s, 0)) for s in stage_order]

    return render(
        request,
        "pipeline/pipeline_list.html",
        {
            "properties": qs,
            "stage_items": stage_items,
            "current_status": status_filter,
            "current_stage": stage_filter,
            "month_filter": month_filter,
            "current_source": source_filter,
            "search_term": search_term,
            "source_choices": [(c.value, c.label) for c in PipelineProperty.SourceType],
            "status_choices": [
                ("ACTIVE", "Active"),
                ("KILLED", "Killed"),
                ("ON_HOLD", "On Hold"),
            ],
        },
    )


@login_required
def pipeline_kanban(request: HttpRequest) -> HttpResponse:
    """Kanban board view: properties grouped by stage with drag-and-drop advance.

    GET:  Renders the board with all active PipelineProperty records
          grouped into stage columns.
    POST: Handles drag-and-drop stage advancement.  Expects
          ``property_id`` and ``new_stage`` in POST body.
          Returns JSON response for the fetch API.
    """
    from core.models import PipelineProperty
    from core.services.pipeline import STAGE_ORDER

    if request.method == "POST":
        pp_id = request.POST.get("property_id")
        new_stage = request.POST.get("new_stage")
        if not pp_id or not new_stage:
            return JsonResponse(
                {"error": "Missing property_id or new_stage"}, status=400
            )
        try:
            pp = PipelineProperty.objects.get(pk=pp_id, user=request.user)
        except PipelineProperty.DoesNotExist:
            return JsonResponse({"error": "Property not found"}, status=404)
        # Validate stage order — only allow forward advancement
        try:
            current_idx = STAGE_ORDER.index(pp.stage)
            new_idx = STAGE_ORDER.index(new_stage)
        except ValueError:
            return JsonResponse({"error": f"Unknown stage: {new_stage}"}, status=400)
        if new_idx <= current_idx:
            return JsonResponse(
                {"error": "Properties can only advance forward"}, status=400
            )
        # Advance one stage at a time (user can drag multiple columns but
        # we process sequentially — the advance_stage service just goes to
        # the next stage regardless of how many columns the user dragged)
        pp.stage = new_stage
        pp.save(update_fields=["stage", "updated_at"])
        return JsonResponse({"status": "ok", "stage": pp.stage})

    # GET: Build stage columns
    qs = PipelineProperty.objects.filter(
        user=request.user, status=PipelineProperty.Status.ACTIVE
    ).select_related("investment_analysis")

    stages = STAGE_ORDER[:7]  # DISCOVERED through CLOSING
    columns: list[dict] = []
    for stage in stages:
        props = [p for p in qs if p.stage == stage]
        columns.append(
            {
                "stage": stage,
                "label": PipelineProperty.Stage(stage).label,
                "properties": props,
                "count": len(props),
            }
        )

    # Growth areas for the discovery modal
    user_growth_areas = GrowthArea.objects.order_by("-composite_score")[:20]

    return render(
        request,
        "pipeline/kanban.html",
        {
            "columns": columns,
            "all_stages": STAGE_ORDER,
            "user_growth_areas": user_growth_areas,
        },
    )


@login_required
def pipeline_review_queue(request: HttpRequest) -> HttpResponse:
    """Review queue: SCREENING-passed properties ready for triage.

    Shows only PipelineProperty records at the SCREENING stage with
    ``screening_passed=True``, sorted by ``gacs_score`` descending
    (nulls last), then by ``created_at``.
    """
    from core.models import PipelineProperty

    qs = (
        PipelineProperty.objects.filter(
            user=request.user,
            status=PipelineProperty.Status.ACTIVE,
            stage=PipelineProperty.Stage.SCREENING,
            screening_passed=True,
        )
        .select_related("investment_analysis")
        .order_by(F("gacs_score").desc(nulls_last=True), "created_at")
    )

    # Count badges
    count_pass = qs.count()
    count_marginal = PipelineProperty.objects.filter(
        user=request.user,
        status=PipelineProperty.Status.ACTIVE,
        stage=PipelineProperty.Stage.SCREENING,
        screening_passed=False,
    ).count()

    # Paginate
    paginator = Paginator(qs, 20)
    page_num = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_num)

    # Last visit badge (session-based)
    last_visit = request.session.get("pipeline_review_last_visit")
    request.session["pipeline_review_last_visit"] = timezone.now().isoformat()

    return render(
        request,
        "pipeline/review_queue.html",
        {
            "page_obj": page_obj,
            "count_pass": count_pass,
            "count_marginal": count_marginal,
            "last_visit": last_visit,
        },
    )


@login_required
def pipeline_review_csv(request: HttpRequest) -> HttpResponse:
    """Export the review queue as CSV."""
    import csv

    from core.models import PipelineProperty

    qs = (
        PipelineProperty.objects.filter(
            user=request.user,
            status=PipelineProperty.Status.ACTIVE,
            stage=PipelineProperty.Stage.SCREENING,
            screening_passed=True,
        )
        .select_related("investment_analysis")
        .order_by(F("gacs_score").desc(nulls_last=True), "created_at")
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="pipeline_review.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Address",
            "Price",
            "Source Type",
            "GACS Score",
            "Estimated Rent",
            "Beds",
            "Created",
        ]
    )
    for pp in qs:
        writer.writerow(
            [
                pp.address,
                str(pp.price) if pp.price else "",
                pp.get_source_type_display(),
                str(pp.gacs_score) if pp.gacs_score else "",
                str(pp.estimated_rent) if pp.estimated_rent else "",
                str(pp.beds) if pp.beds else "",
                pp.created_at.strftime("%Y-%m-%d") if pp.created_at else "",
            ]
        )
    return response


@login_required
def pipeline_advance_stage(request: HttpRequest, pk: int) -> HttpResponse:
    """Advance a pipeline property to the next stage.

    Accepts POST with ``action`` parameter.  Currently supports:
      - ``hold``: set status to ON_HOLD
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    from core.models import PipelineProperty

    try:
        prop = PipelineProperty.objects.get(pk=pk, user=request.user)
    except PipelineProperty.DoesNotExist:
        raise Http404

    action = request.POST.get("action", "")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or ""

    if action == "hold":
        prop.status = PipelineProperty.Status.ON_HOLD
        prop.save(update_fields=["status", "updated_at"])
        messages.info(request, f"{prop.address} has been moved to Hold.")
    elif action == "advance":
        from core.services.pipeline import advance_stage

        try:
            advance_stage(prop)
            messages.success(
                request, f"{prop.address} advanced to {prop.get_stage_display()}."
            )
        except ValueError as exc:
            messages.warning(request, str(exc))
    else:
        messages.warning(request, f"Unknown action: {action}")

    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}
    ):
        return redirect(next_url)
    return redirect("pipeline_review_queue")


@login_required
def pipeline_advance(request: HttpRequest, pk: int) -> HttpResponse:
    """Advance to next sequential stage via POST."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    from core.models import PipelineProperty
    from core.services.pipeline import advance_stage

    try:
        prop = PipelineProperty.objects.get(pk=pk, user=request.user)
    except PipelineProperty.DoesNotExist:
        raise Http404

    try:
        advance_stage(prop)
        return JsonResponse({"status": "ok", "stage": prop.stage})
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@login_required
def pipeline_kill(request: HttpRequest, pk: int) -> HttpResponse:
    """Kill a pipeline property — set status=KILLED."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    from core.models import PipelineProperty
    from core.services.pipeline import kill_property

    try:
        prop = PipelineProperty.objects.get(pk=pk, user=request.user)
    except PipelineProperty.DoesNotExist:
        raise Http404

    reason = request.POST.get("reason", "No reason provided")
    kill_property(prop, reason)
    return JsonResponse({"status": "ok"})


@login_required
def pipeline_hold(request: HttpRequest, pk: int) -> HttpResponse:
    """Place a pipeline property on hold — set status=ON_HOLD."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    from core.models import PipelineProperty
    from core.services.pipeline import hold_property

    try:
        prop = PipelineProperty.objects.get(pk=pk, user=request.user)
    except PipelineProperty.DoesNotExist:
        raise Http404

    reason = request.POST.get("reason", "")
    hold_property(prop, reason)
    return JsonResponse({"status": "ok"})


@login_required
def pipeline_reactivate(request: HttpRequest, pk: int) -> HttpResponse:
    """Reactivate a KILLED or ON_HOLD property."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    from core.models import PipelineProperty
    from core.services.pipeline import reactivate_property

    try:
        prop = PipelineProperty.objects.get(pk=pk, user=request.user)
    except PipelineProperty.DoesNotExist:
        raise Http404

    reactivate_property(prop)
    return JsonResponse({"status": "ok"})


def pipeline_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Pipeline property detail view.

    Shows all pipeline fields, source record data, stage history,
    and action buttons. 404 if not the user's property.
    """
    from core.models import PipelineProperty
    from core.services.pipeline import get_source_record

    try:
        prop = PipelineProperty.objects.get(pk=pk, user=request.user)
    except PipelineProperty.DoesNotExist:
        raise Http404

    source_record = get_source_record(prop)

    # Stage history: build list of (stage_name, timestamp) skipping None
    stage_fields = [
        ("DISCOVERED", prop.discovered_at),
        ("SCREENING", prop.screening_at),
        ("UNDERWRITING", prop.underwriting_at),
        ("OFFER", prop.offer_at),
        ("DUE_DILIGENCE", prop.due_diligence_at),
        ("CLOSING", prop.closing_at),
        ("ACQUIRED", prop.acquired_at),
        ("RENOVATION", prop.renovation_at),
        ("STABILIZED", prop.stabilized_at),
    ]
    stage_history = [(s, t) for s, t in stage_fields if t is not None]

    # Days in pipeline
    if prop.discovered_at:
        days_in_pipeline = (timezone.now() - prop.discovered_at).days
    else:
        days_in_pipeline = 0

    # Kill reason suggestions (shared with template)
    kill_reasons = [
        "Price too high",
        "Low yield",
        "Poor condition",
        "Bad market",
        "Financing fell through",
        "Lost to other buyer",
        "Failed inspection",
        "Title issues",
        "Other",
    ]

    return render(
        request,
        "pipeline/pipeline_detail.html",
        {
            "prop": prop,
            "source_record": source_record,
            "stage_history": stage_history,
            "days_in_pipeline": days_in_pipeline,
            "kill_reasons": kill_reasons,
        },
    )


@login_required
def pipeline_add_from_source(request: HttpRequest) -> HttpResponse:
    """POST-only view to add a source property to the user's pipeline.

    POST params:
      source_type: 'vrm' (future: 'foreclosure', 'listing')
      source_id:   primary key / identifier of the source record
      next:        redirect URL on error (default: /pipeline/list/)
    """
    from django.shortcuts import redirect

    from core.services.pipeline import create_from_vrm

    if request.method != "POST":
        messages.error(request, "This endpoint requires POST")
        return redirect("pipeline_list")

    source_type = request.POST.get("source_type", "")
    source_id = request.POST.get("source_id", "")
    next_url = request.POST.get("next", redirect("pipeline_list").url)

    if not source_type or not source_id:
        messages.error(request, "Missing source_type or source_id")
        return redirect(next_url)

    if source_type == "vrm":
        try:
            vrm = VrmProperty.objects.get(vrm_property_id=int(source_id))
        except VrmProperty.DoesNotExist, ValueError, TypeError:
            messages.error(request, "VRM property not found")
            return redirect(next_url)

        pp, created = create_from_vrm(vrm, request.user)

        if created:
            verdict = "passed" if pp.screening_passed else "failed"
            messages.success(
                request,
                f"VRM property added to pipeline. Screening {verdict}.",
            )
        else:
            messages.info(request, "Already in your pipeline")

        return redirect("pipeline_detail", pk=pp.pk)

    if source_type == "hud":
        from core.services.pipeline import create_from_hud

        try:
            hud = HudProperty.objects.get(hud_case_number=source_id)
        except HudProperty.DoesNotExist:
            messages.error(request, "HUD property not found")
            return redirect(next_url)

        pp, created = create_from_hud(hud, request.user)

        if created:
            verdict = "passed" if pp.screening_passed else "failed"
            messages.success(
                request,
                f"HUD property added to pipeline. Screening {verdict}.",
            )
        else:
            messages.info(request, "Already in your pipeline")

        return redirect("pipeline_detail", pk=pp.pk)

    if source_type == "usda":
        from core.services.pipeline import create_from_usda

        try:
            usda = UsdaProperty.objects.get(usda_case_number=source_id)
        except UsdaProperty.DoesNotExist:
            messages.error(request, "USDA property not found")
            return redirect(next_url)

        pp, created = create_from_usda(usda, request.user)

        if created:
            verdict = "passed" if pp.screening_passed else "failed"
            messages.success(
                request,
                f"USDA property added to pipeline. Screening {verdict}.",
            )
        else:
            messages.info(request, "Already in your pipeline")

        return redirect("pipeline_detail", pk=pp.pk)

    if source_type in ("attom", "county"):
        from core.integrations.sources.attom_preforeclosure import (
            fetch_attom_preforeclosure,
        )
        from core.models import CountyForeclosureNotice
        from core.services.pipeline import create_from_county_notice

        if source_type == "attom":
            # For ATTOM, source_id is a ZIP code — fetch via API, then upsert
            notices = fetch_attom_preforeclosure(zip_code=source_id)
            if not notices:
                messages.warning(
                    request, "No ATTOM preforeclosure notices found for that ZIP."
                )
                return redirect(next_url)

            count = 0
            for notice_data in notices:
                notice_data.pop("scraped_at", None)
                notice_data.pop("last_seen_at", None)
                cn, _ = CountyForeclosureNotice.objects.update_or_create(
                    case_number=notice_data["case_number"],
                    county=notice_data.get("county", ""),
                    state=notice_data.get("state", ""),
                    defaults=notice_data,
                )
                pp, created = create_from_county_notice(cn, request.user)
                if created:
                    count += 1

            messages.success(request, f"{count} ATTOM notice(s) added to pipeline.")
            return redirect("pipeline_list")
        else:
            # county: source_id is a CountyForeclosureNotice pk
            try:
                cn = CountyForeclosureNotice.objects.get(pk=int(source_id))
            except CountyForeclosureNotice.DoesNotExist, ValueError, TypeError:
                messages.error(request, "County notice not found")
                return redirect(next_url)

            pp, created = create_from_county_notice(cn, request.user)

            if created:
                messages.success(request, "County notice added to pipeline.")
            else:
                messages.info(request, "Already in your pipeline")

            return redirect("pipeline_detail", pk=pp.pk)

    messages.error(request, f"Unknown source type: {source_type}")
    return redirect(next_url)


@login_required
def pipeline_offer_create(request: HttpRequest, pk: int) -> HttpResponse:
    """Create or list offers for a pipeline property."""
    from core.models import OfferRecord, PipelineProperty

    try:
        prop = PipelineProperty.objects.get(pk=pk, user=request.user)
    except PipelineProperty.DoesNotExist:
        raise Http404

    existing_offers = OfferRecord.objects.filter(pipeline_property=prop).order_by(
        "-created_at"
    )

    if request.method == "POST":
        from datetime import date

        offer_price = request.POST.get("offer_price")
        offer_date = request.POST.get("offer_date", str(date.today()))
        offer_expiry = request.POST.get("offer_expiry") or None
        contingencies = request.POST.getlist("contingencies")
        notes = request.POST.get("notes", "")

        if not offer_price:
            messages.error(request, "Offer price is required.")
            return redirect("pipeline_offer_create", pk=pk)

        OfferRecord.objects.create(
            pipeline_property=prop,
            offer_price=Decimal(offer_price),
            offer_date=offer_date,
            offer_expiry=offer_expiry,
            contingencies=contingencies,
            notes=notes,
        )
        messages.success(request, "Offer recorded.")
        return redirect("pipeline_offer_create", pk=pk)

    return render(
        request,
        "pipeline/offer_form.html",
        {
            "prop": prop,
            "offers": existing_offers,
        },
    )


@login_required
def pipeline_dd_checklist(request: HttpRequest, pk: int) -> HttpResponse:
    """View and edit due diligence checklist for a pipeline property."""
    from core.models import DueDiligenceChecklist, PipelineProperty
    from core.services.pipeline import kill_property

    try:
        prop = PipelineProperty.objects.get(pk=pk, user=request.user)
    except PipelineProperty.DoesNotExist:
        raise Http404

    dd, created = DueDiligenceChecklist.objects.get_or_create(
        pipeline_property=prop,
    )

    if request.method == "POST":
        dd.inspection_scheduled = "inspection_scheduled" in request.POST
        dd.inspection_completed = "inspection_completed" in request.POST
        dd.inspection_findings = request.POST.get("inspection_findings", "")
        dd.title_search_ordered = "title_search_ordered" in request.POST
        dd.title_clear = (
            True
            if "title_clear" in request.POST
            else (False if "title_clear_no" in request.POST else None)
        )
        dd.appraisal_ordered = "appraisal_ordered" in request.POST
        appraisal_val = request.POST.get("appraisal_value", "").strip()
        dd.appraisal_value = Decimal(appraisal_val) if appraisal_val else None
        dd.insurance_quoted = "insurance_quoted" in request.POST
        insurance_cost = request.POST.get("insurance_annual_cost", "").strip()
        dd.insurance_annual_cost = Decimal(insurance_cost) if insurance_cost else None
        dd.contractor_estimate_obtained = "contractor_estimate_obtained" in request.POST
        contractor_est = request.POST.get("contractor_estimate_amount", "").strip()
        dd.contractor_estimate_amount = (
            Decimal(contractor_est) if contractor_est else None
        )
        dd.go_no_go = request.POST.get("go_no_go", "pending")
        dd.no_go_reason = request.POST.get("no_go_reason", "")
        dd.save()

        if dd.go_no_go == "no_go" and dd.no_go_reason:
            kill_property(prop, dd.no_go_reason)
            messages.success(request, "Property killed due to DD findings.")
        else:
            messages.success(request, "Due diligence checklist saved.")

        return redirect("pipeline_dd_checklist", pk=pk)

    return render(
        request,
        "pipeline/dd_checklist.html",
        {
            "prop": prop,
            "dd": dd,
        },
    )


@login_required
def pipeline_renovation(request: HttpRequest, pk: int) -> HttpResponse:
    """View and edit renovation record for a pipeline property."""
    from core.models import PipelineProperty, RenovationRecord

    try:
        prop = PipelineProperty.objects.get(pk=pk, user=request.user)
    except PipelineProperty.DoesNotExist:
        raise Http404

    renovation, created = RenovationRecord.objects.get_or_create(
        pipeline_property=prop,
    )

    if request.method == "POST":
        est_budget = request.POST.get("estimated_budget", "").strip()
        if est_budget:
            renovation.estimated_budget = Decimal(est_budget)
        start_date = request.POST.get("start_date", "").strip()
        renovation.start_date = start_date or None
        renovation.contractor = request.POST.get("contractor", "")
        renovation.scope_of_work = request.POST.get("scope_of_work", "")
        renovation.status = request.POST.get("status", "not_started")
        completion_date = request.POST.get("completion_date", "").strip()
        renovation.completion_date = completion_date or None
        actual_cost = request.POST.get("actual_cost", "").strip()
        renovation.actual_cost = Decimal(actual_cost) if actual_cost else None
        renovation.notes = request.POST.get("notes", "")
        renovation.save()

        messages.success(request, "Renovation record saved.")
        return redirect("pipeline_renovation", pk=pk)

    return render(
        request,
        "pipeline/renovation_form.html",
        {
            "prop": prop,
            "renovation": renovation,
        },
    )


@login_required
def pipeline_closing_create(request: HttpRequest, pk: int) -> HttpResponse:
    """Create closing record and convert pipeline property to Property.

    On POST: saves ClosingRecord, calls convert_to_property_record(),
    all in transaction.atomic(). Redirects to portfolio dashboard
    on success.
    """
    from django.db import transaction as db_transaction

    from core.models import ClosingRecord, PipelineProperty
    from core.services.pipeline import convert_to_property_record

    try:
        prop = PipelineProperty.objects.get(pk=pk, user=request.user)
    except PipelineProperty.DoesNotExist:
        raise Http404

    # Check for existing closing record
    closing_exists = ClosingRecord.objects.filter(pipeline_property=prop).exists()

    if request.method == "POST":
        final_price = request.POST.get("final_purchase_price")
        closing_date_str = request.POST.get("closing_date")
        closing_costs = request.POST.get("closing_costs", "0")
        loan_amount = request.POST.get("loan_amount", "").strip()
        down_payment = request.POST.get("down_payment", "").strip()
        lender = request.POST.get("lender", "")
        notes = request.POST.get("notes", "")

        if not final_price or not closing_date_str:
            messages.error(
                request, "Final purchase price and closing date are required."
            )
            return redirect("pipeline_closing_create", pk=pk)

        if closing_exists:
            messages.error(
                request,
                "A closing record already exists for this property. "
                "Cannot convert twice.",
            )
            return redirect("pipeline_detail", pk=pk)

        with db_transaction.atomic():
            # Create ClosingRecord
            ClosingRecord.objects.create(
                pipeline_property=prop,
                final_purchase_price=Decimal(final_price),
                closing_date=closing_date_str,
                closing_costs=Decimal(closing_costs),
                loan_amount=Decimal(loan_amount) if loan_amount else None,
                down_payment=Decimal(down_payment) if down_payment else None,
                lender=lender,
                notes=notes,
            )

            # Convert to Property record
            from datetime import datetime

            closing_dt = datetime.strptime(closing_date_str, "%Y-%m-%d").date()
            convert_to_property_record(prop, closing_date=closing_dt)

        messages.success(
            request,
            f"Property acquired at {prop.address}! "
            "Complete your property record to begin portfolio tracking.",
        )
        return redirect("portfolio_dashboard")

    return render(
        request,
        "pipeline/closing_form.html",
        {
            "prop": prop,
            "closing_exists": closing_exists,
        },
    )
