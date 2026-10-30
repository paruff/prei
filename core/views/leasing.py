from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.models import (
    Property,
)


@login_required
def leasing_list(request: HttpRequest) -> HttpResponse:
    """List leasing pipeline entries for the current user."""
    from datetime import date

    from core.models import LeasingPipelineProperty

    status_filter = request.GET.get("status", "ACTIVE")

    qs = LeasingPipelineProperty.objects.filter(
        user=request.user,
        status=status_filter,
    ).order_by("-updated_at")

    # Compute days_vacant for listing-stage entries
    today = date.today()
    for entry in qs:
        if entry.listed_date and entry.stage == "LISTING":
            entry.days_vacant = (today - entry.listed_date).days
        else:
            entry.days_vacant = None

    stage_order = [
        "LISTING",
        "SHOWING",
        "APPLICATION",
        "SCREENING",
        "APPROVED",
        "LEASE_SIGNED",
        "MOVE_IN",
        "STABILIZED",
    ]

    return render(
        request,
        "leasing/leasing_list.html",
        {
            "entries": qs,
            "current_status": status_filter,
            "stage_order": stage_order,
        },
    )


@login_required
def leasing_kanban(request: HttpRequest) -> HttpResponse:
    """Kanban board for the leasing pipeline — drag-and-drop stage advancement.

    Columns: LISTING → SHOWING → APPLICATION → SCREENING → APPROVED →
             LEASE_SIGNED → MOVE_IN → STABILIZED
    """
    from datetime import date

    from core.models import LeasingPipelineProperty

    qs = LeasingPipelineProperty.objects.filter(
        user=request.user, status=LeasingPipelineProperty.Status.ACTIVE
    ).select_related("property_record")

    LEASING_STAGES = [
        "LISTING",
        "SHOWING",
        "APPLICATION",
        "SCREENING",
        "APPROVED",
        "LEASE_SIGNED",
        "MOVE_IN",
        "STABILIZED",
    ]

    if request.method == "POST":
        pp_id = request.POST.get("property_id")
        new_stage = request.POST.get("new_stage")
        if not pp_id or not new_stage:
            return JsonResponse(
                {"error": "Missing property_id or new_stage"}, status=400
            )
        try:
            lp = LeasingPipelineProperty.objects.get(pk=pp_id, user=request.user)
        except LeasingPipelineProperty.DoesNotExist:
            return JsonResponse({"error": "Property not found"}, status=404)
        try:
            new_idx = LEASING_STAGES.index(new_stage)
            current_idx = LEASING_STAGES.index(lp.stage)
        except ValueError:
            return JsonResponse({"error": f"Unknown stage: {new_stage}"}, status=400)
        if new_idx <= current_idx:
            return JsonResponse(
                {"error": "Properties can only advance forward"}, status=400
            )
        lp.stage = new_stage
        lp.save(update_fields=["stage", "updated_at"])
        return JsonResponse({"status": "ok", "stage": lp.stage})

    # GET: Build stage columns
    today = date.today()
    columns: list[dict] = []
    for stage in LEASING_STAGES:
        props = [p for p in qs if p.stage == stage]
        columns.append(
            {
                "stage": stage,
                "label": LeasingPipelineProperty.Stage(stage).label,
                "properties": props,
                "count": len(props),
            }
        )

    return render(
        request,
        "leasing/leasing_kanban.html",
        {
            "columns": columns,
            "today": today,
        },
    )


@login_required
def leasing_add(request: HttpRequest) -> HttpResponse:
    """Add a new leasing pipeline entry."""
    from core.models import LeasingPipelineProperty

    # Properties not already in active leasing
    active_leasing_ids = LeasingPipelineProperty.objects.filter(
        user=request.user,
        status__in=["ACTIVE", "ON_HOLD"],
    ).values_list("property_record_id", flat=True)

    available_properties = (
        Property.objects.filter(
            user=request.user,
        )
        .exclude(pk__in=active_leasing_ids)
        .order_by("address")
    )

    # Pre-fill from ?property_id=
    prefill_property_id = request.GET.get("property_id", "")
    prefill_property = None
    if prefill_property_id:
        try:
            prefill_property = Property.objects.get(
                pk=prefill_property_id,
                user=request.user,
            )
        except Property.DoesNotExist:
            pass

    if request.method == "POST":
        prop_id = request.POST.get("property_record")
        asking_rent = request.POST.get("asking_rent", "").strip()
        listed_date = request.POST.get("listed_date", "").strip()
        listing_source = request.POST.get("listing_source", "")

        if not prop_id:
            messages.error(request, "Please select a property.")
            return redirect("leasing_add")

        try:
            prop = Property.objects.get(pk=prop_id, user=request.user)
        except Property.DoesNotExist:
            messages.error(request, "Property not found.")
            return redirect("leasing_add")

        LeasingPipelineProperty.objects.create(
            property_record=prop,
            user=request.user,
            asking_rent=Decimal(asking_rent) if asking_rent else None,
            listed_date=listed_date or None,
            listing_source=listing_source,
        )
        messages.success(request, "Property added to leasing pipeline.")
        return redirect("leasing_list")

    return render(
        request,
        "leasing/leasing_add.html",
        {
            "available_properties": available_properties,
            "prefill_property": prefill_property,
        },
    )


@login_required
def leasing_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Leasing pipeline detail view."""
    from core.models import LeasingPipelineProperty

    try:
        entry = LeasingPipelineProperty.objects.get(pk=pk, user=request.user)
    except LeasingPipelineProperty.DoesNotExist:
        raise Http404

    # Stage history: chronological from stage based on created_at/updated_at
    stage_order = [
        "LISTING",
        "SHOWING",
        "APPLICATION",
        "SCREENING",
        "APPROVED",
        "LEASE_SIGNED",
        "MOVE_IN",
        "STABILIZED",
    ]
    stage_history = [
        (s, None) for s in stage_order[: stage_order.index(entry.stage) + 1]
    ]

    return render(
        request,
        "leasing/leasing_detail.html",
        {
            "entry": entry,
            "stage_history": stage_history,
            "stage_order": stage_order,
        },
    )


@login_required
def leasing_showing(request: HttpRequest, pk: int) -> HttpResponse:
    """Record a showing for a leasing property."""
    from core.models import LeasingPipelineProperty

    entry = get_object_or_404(LeasingPipelineProperty, pk=pk, user=request.user)
    if request.method == "POST":
        advance = request.POST.get("advance")
        entry.stage = LeasingPipelineProperty.Stage.SHOWING
        entry.save(update_fields=["stage", "updated_at"])
        messages.success(request, "Showing recorded.")
        if advance:
            try:
                from core.services.leasing import advance_stage

                advance_stage(entry)
                messages.success(request, f"Advanced to {entry.get_stage_display()}.")
            except ValueError as e:
                messages.warning(request, str(e))
        return redirect("leasing_detail", pk=pk)
    return render(
        request,
        "leasing/stage_form.html",
        {
            "entry": entry,
            "action": "Record Showing",
            "stage": "SHOWING",
        },
    )


@login_required
def leasing_application(request: HttpRequest, pk: int) -> HttpResponse:
    """Record an application with applicant details."""
    from core.models import LeasingPipelineProperty

    entry = get_object_or_404(LeasingPipelineProperty, pk=pk, user=request.user)
    if request.method == "POST":
        entry.applicant_name = request.POST.get("applicant_name", "")
        entry.application_date = (
            request.POST.get("application_date") or timezone.now().date()
        )
        entry.stage = LeasingPipelineProperty.Stage.APPLICATION
        entry.save(
            update_fields=["applicant_name", "application_date", "stage", "updated_at"]
        )
        messages.success(request, "Application recorded.")
        return redirect("leasing_detail", pk=pk)
    return render(
        request,
        "leasing/stage_form.html",
        {
            "entry": entry,
            "action": "Record Application",
            "stage": "APPLICATION",
        },
    )


@login_required
def leasing_screening(request: HttpRequest, pk: int) -> HttpResponse:
    """Record screening result (pass/fail) and optionally advance."""
    from core.models import LeasingPipelineProperty

    entry = get_object_or_404(LeasingPipelineProperty, pk=pk, user=request.user)
    if request.method == "POST":
        entry.screening_passed = request.POST.get("screening_passed") == "true"
        entry.screening_notes = request.POST.get("screening_notes", "")
        entry.stage = LeasingPipelineProperty.Stage.SCREENING
        entry.save(
            update_fields=["screening_passed", "screening_notes", "stage", "updated_at"]
        )
        if request.POST.get("advance") and entry.screening_passed:
            try:
                from core.services.leasing import advance_stage

                advance_stage(entry)
            except ValueError:
                pass
        messages.success(request, "Screening result saved.")
        return redirect("leasing_detail", pk=pk)
    return render(
        request,
        "leasing/stage_form.html",
        {
            "entry": entry,
            "action": "Applicant Screening",
            "stage": "SCREENING",
        },
    )


@login_required
def leasing_lease(request: HttpRequest, pk: int) -> HttpResponse:
    """Record lease details (start date, end date, monthly rent)."""
    from core.models import LeasingPipelineProperty

    entry = get_object_or_404(LeasingPipelineProperty, pk=pk, user=request.user)
    if request.method == "POST":
        entry.lease_start_date = request.POST.get("lease_start_date")
        entry.lease_end_date = request.POST.get("lease_end_date") or None
        entry.monthly_rent = Decimal(request.POST.get("monthly_rent", 0))
        entry.stage = LeasingPipelineProperty.Stage.LEASE_SIGNED
        entry.save(
            update_fields=[
                "lease_start_date",
                "lease_end_date",
                "monthly_rent",
                "stage",
                "updated_at",
            ]
        )
        messages.success(request, "Lease recorded.")
        return redirect("leasing_detail", pk=pk)
    return render(
        request,
        "leasing/stage_form.html",
        {
            "entry": entry,
            "action": "Record Lease",
            "stage": "LEASE_SIGNED",
        },
    )


@login_required
def leasing_move_in(request: HttpRequest, pk: int) -> HttpResponse:
    """Record move-in completion."""
    from core.models import LeasingPipelineProperty

    entry = get_object_or_404(LeasingPipelineProperty, pk=pk, user=request.user)
    if request.method == "POST":
        entry.move_in_date = request.POST.get("move_in_date") or timezone.now().date()
        entry.stage = LeasingPipelineProperty.Stage.MOVE_IN
        entry.save(update_fields=["move_in_date", "stage", "updated_at"])
        messages.success(request, "Move-in recorded.")
        return redirect("leasing_detail", pk=pk)
    return render(
        request,
        "leasing/stage_form.html",
        {
            "entry": entry,
            "action": "Record Move-In",
            "stage": "MOVE_IN",
        },
    )


@login_required
def leasing_stabilize(request: HttpRequest, pk: int) -> HttpResponse:
    """Mark a leasing property as stabilized."""
    from core.models import LeasingPipelineProperty

    entry = get_object_or_404(LeasingPipelineProperty, pk=pk, user=request.user)
    if request.method == "POST":
        entry.stabilized_date = (
            request.POST.get("stabilized_date") or timezone.now().date()
        )
        entry.stage = LeasingPipelineProperty.Stage.STABILIZED
        entry.status = LeasingPipelineProperty.Status.FILLED
        entry.save(update_fields=["stabilized_date", "stage", "status", "updated_at"])
        messages.success(request, "Property stabilized.")
        return redirect("leasing_detail", pk=pk)
    return render(
        request,
        "leasing/stage_form.html",
        {
            "entry": entry,
            "action": "Mark Stabilized",
            "stage": "STABILIZED",
        },
    )
