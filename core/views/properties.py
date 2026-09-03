from __future__ import annotations

from decimal import Decimal
from typing import cast

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import (
    Http404,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
)
from django.shortcuts import get_object_or_404, redirect, render

from core.forms import (
    CapExItemForm,
    OperatingExpenseForm,
    PropertyForm,
    RentalIncomeForm,
)
from core.models import (
    CapExItem,
    Property,
    PropertyShare,
    UserInvestmentTargets,
)
from core.services import compute_portfolio_summary

from core.services.financing_comparison import compare_scenarios, get_best_scenario

from investor_app.finance.utils import (
    compute_analysis_for_property,
)

from .permissions import _get_property_role, _is_client_only_user, is_owner_or_shared

User = get_user_model()


@login_required
def property_list(request):
    properties = (
        Property.objects.filter(
            Q(user=request.user) | Q(property_shares__shared_with=request.user)
        )
        .select_related("analysis")
        .distinct()
        .order_by("-id")
    )
    property_ids = list(properties.values_list("id", flat=True))
    share_roles_by_property_id = dict(
        PropertyShare.objects.filter(
            shared_with=request.user,
            property_id__in=property_ids,
        ).values_list("property_id", "role")
    )

    # Compute underwriting score for each property
    from core.services.scoring import score_listing_v2

    try:
        targets = UserInvestmentTargets.objects.get(user=request.user)
    except UserInvestmentTargets.DoesNotExist:
        targets = None

    for property_obj in properties:
        property_obj.access_role = (
            "owner"
            if property_obj.user_id == request.user.id
            else share_roles_by_property_id.get(property_obj.id, "client")
        )
        # Attach scoring data
        property_obj.underwriting_score = None
        if targets:
            try:
                property_obj.underwriting_score = score_listing_v2(
                    property_obj, targets
                )
            except Exception:
                pass

    return render(
        request,
        "properties/list.html",
        {
            "properties": properties,
            "portfolio_summary": compute_portfolio_summary(request.user),
            "can_add_property": not _is_client_only_user(request.user),
        },
    )


def _parse_compare_ids(raw_ids: list[str]) -> tuple[list[int], str | None]:
    """Parse property IDs from repeated/comma-separated query parameter values.

    Args:
        raw_ids: Raw `ids` query values from request.GET.getlist("ids").

    Returns:
        tuple[list[int], str | None]: Parsed positive integer IDs and optional
        validation error message.
    """
    parsed_ids: list[int] = []
    for raw_id in raw_ids:
        for token in raw_id.split(","):
            stripped = token.strip()
            if not stripped:
                continue
            try:
                parsed_id = int(stripped)
            except ValueError:
                return [], "Property IDs must be integers."
            if parsed_id > 0:
                parsed_ids.append(parsed_id)
    return parsed_ids, None


@login_required
def property_compare(request):
    parsed_ids, parse_error = _parse_compare_ids(request.GET.getlist("ids"))
    if parse_error:
        return render(
            request,
            "properties/compare.html",
            {"error_message": parse_error},
            status=400,
        )

    # Preserve user-selected order so comparison columns are stable and predictable.
    unique_ids = list(dict.fromkeys(parsed_ids))

    if len(unique_ids) < 2:
        return render(
            request,
            "properties/compare.html",
            {"error_message": "Select at least 2 properties to compare."},
            status=400,
        )

    warning_message = None
    if len(unique_ids) > 4:
        unique_ids = unique_ids[:4]
        warning_message = "You can compare up to 4 properties at once. Showing the first 4 selections."

    properties = list(
        Property.objects.filter(
            Q(user=request.user) | Q(property_shares__shared_with=request.user),
            id__in=unique_ids,
        )
        .select_related("analysis")
        .prefetch_related("rental_incomes")
        .distinct()
    )
    properties_by_id = {property_obj.id: property_obj for property_obj in properties}
    if len(properties_by_id) != len(unique_ids):
        raise Http404(
            "One or more selected properties were not found or are not accessible."
        )

    ordered_properties = [properties_by_id[property_id] for property_id in unique_ids]
    property_data: list[dict[str, object]] = []
    for property_obj in ordered_properties:
        analysis = getattr(property_obj, "analysis", None)
        if analysis is None:
            analysis = compute_analysis_for_property(property_obj)
        rental_incomes = list(property_obj.rental_incomes.all())
        rental_income = max(
            rental_incomes,
            key=lambda income: (income.effective_date, income.id),
            default=None,
        )
        property_data.append(
            {
                "property": property_obj,
                "metrics": {
                    "noi": analysis.noi,
                    "cap_rate": analysis.cap_rate,
                    "cash_on_cash": analysis.cash_on_cash,
                    "irr": analysis.irr,
                    "dscr": analysis.dscr,
                    "purchase_price": property_obj.purchase_price,
                    "monthly_rent": (
                        rental_income.monthly_rent if rental_income else Decimal("0")
                    ),
                    "vacancy_rate": (
                        rental_income.vacancy_rate if rental_income else Decimal("0")
                    ),
                },
            }
        )

    comparison_rows = [
        {"label": "NOI", "key": "noi", "format": "currency", "higher_is_better": True},
        {
            "label": "Cap Rate",
            "key": "cap_rate",
            "format": "decimal4",
            "higher_is_better": True,
        },
        {
            "label": "Cash-on-Cash",
            "key": "cash_on_cash",
            "format": "decimal4",
            "higher_is_better": True,
        },
        {"label": "IRR", "key": "irr", "format": "decimal4", "higher_is_better": True},
        {
            "label": "DSCR",
            "key": "dscr",
            "format": "decimal4",
            "higher_is_better": True,
        },
        {
            "label": "Purchase Price",
            "key": "purchase_price",
            "format": "currency",
            "higher_is_better": False,
        },
        {
            "label": "Monthly Rent",
            "key": "monthly_rent",
            "format": "currency",
            "higher_is_better": True,
        },
        {
            "label": "Vacancy Rate",
            "key": "vacancy_rate",
            "format": "decimal4",
            "higher_is_better": False,
        },
    ]

    for row in comparison_rows:
        key = cast(str, row["key"])
        row_values = [
            {
                "property_id": cast(Property, item["property"]).id,
                "value": cast(Decimal, item["metrics"][key]),
            }
            for item in property_data
        ]
        values = [cast(Decimal, item["value"]) for item in row_values]
        best_value = max(values) if row["higher_is_better"] else min(values)
        worst_value = min(values) if row["higher_is_better"] else max(values)
        row["values"] = row_values
        if best_value == worst_value:
            # Avoid ambiguous highlights when every value is identical.
            row["best_property_ids"] = []
            row["worst_property_ids"] = []
            continue
        row["best_property_ids"] = [
            cast(int, item["property_id"])
            for item in row_values
            if cast(Decimal, item["value"]) == best_value
        ]
        row["worst_property_ids"] = [
            cast(int, item["property_id"])
            for item in row_values
            if cast(Decimal, item["value"]) == worst_value
        ]

    return render(
        request,
        "properties/compare.html",
        {
            "property_data": property_data,
            "comparison_rows": comparison_rows,
            "warning_message": warning_message,
        },
    )


@login_required
def property_detail(request, pk: int):
    property_obj = get_object_or_404(Property.objects.select_related("analysis"), pk=pk)
    if not is_owner_or_shared(request.user, property_obj, min_role="client"):
        raise Http404
    user_role = _get_property_role(request.user, property_obj)

    # Compute underwriting score
    from core.services.scoring import score_listing_v2

    score = None
    targets = None
    try:
        targets, _ = UserInvestmentTargets.objects.get_or_create(user=property_obj.user)
        score = score_listing_v2(property_obj, targets)
    except Exception:
        pass

    # Compute 10-year projections for the detail view
    projections = None
    exit_analysis = None
    try:
        from core.services.projections import project_hold_period

        projections, exit_analysis = project_hold_period(property_obj, hold_years=10)
    except Exception:
        # Projections are optional; don't break the page if they fail
        pass

    return render(
        request,
        "properties/detail.html",
        {
            "property": property_obj,
            "analysis": getattr(property_obj, "analysis", None),
            "score": score,
            "targets": targets,
            "projection": projections,
            "exit": exit_analysis,
            "can_edit_property": user_role in {"owner", "team"},
            "can_share_property": user_role == "owner",
        },
    )


@login_required
def financing_comparison(request, pk: int):
    """Show financing scenario comparison for a property."""
    property_obj = get_object_or_404(Property, pk=pk)
    if not is_owner_or_shared(request.user, property_obj, min_role="client"):
        raise Http404
    user_role = _get_property_role(request.user, property_obj)

    # Compare scenarios
    results = compare_scenarios(property_obj)

    # Find best scenarios
    best_coc = get_best_scenario(results, "cash_on_cash")
    best_dscr = get_best_scenario(results, "dscr")

    return render(
        request,
        "properties/financing_comparison.html",
        {
            "property": property_obj,
            "results": results,
            "best_coc": best_coc,
            "best_dscr": best_dscr,
            "can_edit": user_role in {"owner", "team"},
        },
    )


@login_required
def property_add(request):
    if _is_client_only_user(request.user):
        return HttpResponseForbidden("Client users have read-only access.")
    if request.method == "POST":
        form = PropertyForm(request.POST)
        if form.is_valid():
            property_obj = form.save(commit=False)
            property_obj.user = request.user
            property_obj.save()

            # Create default CapEx items based on property age
            from core.services.capex import get_default_capex_items_for_age

            property_age = 0
            if property_obj.purchase_date:
                from django.utils import timezone

                property_age = (
                    timezone.now().date() - property_obj.purchase_date
                ).days // 365
            for item in get_default_capex_items_for_age(property_age):
                property_obj.capex_items.create(
                    component_type=item.component_type,
                    replacement_cost=item.replacement_cost,
                    useful_life_years=item.useful_life_years,
                    age_years=item.age_years,
                )

            compute_analysis_for_property(property_obj)
            return redirect("property_detail", pk=property_obj.pk)
    else:
        form = PropertyForm()

    return render(request, "property_form.html", {"form": form})


@login_required
def property_edit(request, pk: int):
    property_obj = get_object_or_404(Property, pk=pk)
    if not is_owner_or_shared(request.user, property_obj, min_role="team"):
        raise Http404
    user_role = _get_property_role(request.user, property_obj)
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
        "property_form.html",
        {
            "form": form,
            "object": property_obj,
            "can_delete_property": user_role == "owner",
        },
    )


@login_required
def capex_item_edit(request, pk: int):
    capex_item = get_object_or_404(CapExItem, pk=pk)
    property_obj = capex_item.prop
    if not is_owner_or_shared(request.user, property_obj, min_role="team"):
        raise Http404
    if request.method == "POST":
        form = CapExItemForm(request.POST, instance=capex_item)
        if form.is_valid():
            form.save()
            return redirect("property_detail", pk=property_obj.pk)
    else:
        form = CapExItemForm(instance=capex_item)

    return render(
        request,
        "properties/capex_item_edit.html",
        {
            "form": form,
            "capex_item": capex_item,
            "property": property_obj,
        },
    )


@login_required
def property_delete(request, pk: int):
    property_obj = get_object_or_404(Property, pk=pk)
    if property_obj.user_id != request.user.id:
        raise Http404
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    property_obj.delete()
    return redirect("property_list")


@login_required
def property_add_income(request, pk: int):
    property_obj = get_object_or_404(Property, pk=pk)
    if not is_owner_or_shared(request.user, property_obj, min_role="team"):
        raise Http404
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
    property_obj = get_object_or_404(Property, pk=pk)
    if not is_owner_or_shared(request.user, property_obj, min_role="team"):
        raise Http404
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


@login_required
def property_share(request, pk: int):
    property_obj = get_object_or_404(Property, pk=pk, user=request.user)
    error = ""
    if request.method == "POST":
        revoke_share_id = request.POST.get("revoke_share_id")
        if revoke_share_id:
            PropertyShare.objects.filter(
                id=revoke_share_id, property=property_obj
            ).delete()
            return redirect("property_share", pk=property_obj.pk)

        email = request.POST.get("email", "").strip()
        role = request.POST.get("role", "")
        if role not in dict(PropertyShare.ROLE_CHOICES):
            error = "Invalid role selected."
        else:
            shared_user = User.objects.filter(email__iexact=email).first()
            if shared_user is None:
                error = "No user found for that email."
            elif shared_user.id == request.user.id:
                error = "You already own this property."
            else:
                PropertyShare.objects.update_or_create(
                    property=property_obj,
                    shared_with=shared_user,
                    defaults={"role": role},
                )
                return redirect("property_share", pk=property_obj.pk)

    shares = PropertyShare.objects.filter(property=property_obj).select_related(
        "shared_with"
    )
    return render(
        request,
        "properties/share.html",
        {
            "property": property_obj,
            "shares": shares,
            "role_choices": PropertyShare.ROLE_CHOICES,
            "error": error,
        },
    )
