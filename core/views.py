from __future__ import annotations

import io
import logging
from io import BytesIO
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Protocol, cast

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify
from django.views import View
from xhtml2pdf import pisa

from .models import VrmProperty, UserInvestmentTargets, GrowthArea

from investor_app.finance.utils import (
    compute_analysis_for_property,
    calculate_whatif_monthly_cashflow,
    score_listing_v1,
)

# keep only the models that are actually used
from core.services.cma import estimate_listing_kpis, find_undervalued, price_per_sqft
from core.services import compute_portfolio_summary
from core.services.audit import log_action
from .forms import (
    OperatingExpenseForm,
    PropertyForm,
    RentalIncomeForm,
    InvestmentTargetsForm,
)
from .models import (
    Listing,
    MarketSnapshot,
    Property,
    PropertyShare,
    SavedSearch,
    Transaction,
)

logger = logging.getLogger(__name__)
FinancingValue = str | int | float | Decimal | None
User = get_user_model()
ROLE_RANK = {"client": 1, "team": 2, "owner": 3}


class AuthenticatedUser(Protocol):
    """Minimal authenticated-user contract used by RBAC helper functions.

    The RBAC helpers only require a persisted integer ``id`` and do not depend on
    ``AbstractBaseUser`` fields, which avoids ORM typing mismatches in mypy while
    remaining compatible with configured auth user models.

    Attributes:
        id: Persisted primary key for the authenticated user.
    """

    id: int


def _get_property_role(user: AuthenticatedUser, property_obj: Property) -> str | None:
    """Return the caller's role for the property, if any.

    Args:
        user: Authenticated request user with a persisted integer id.
        property_obj: Property being authorized.

    Returns:
        str | None: "owner", "team", or "client" when access exists; otherwise None.
    """
    if property_obj.user_id == user.id:
        return "owner"
    share = PropertyShare.objects.filter(
        property=property_obj, shared_with_id=user.id
    ).first()
    if share is None:
        return None
    return share.role


def is_owner_or_shared(
    user: AuthenticatedUser, property_obj: Property, min_role: str = "client"
) -> bool:
    """Check whether user meets or exceeds the minimum property access role.

    Args:
        user: Authenticated request user with a persisted integer id.
        property_obj: Property being authorized.
        min_role: Minimum accepted role ("client", "team", or "owner").

    Returns:
        bool: True when the user's role rank is at least min_role; otherwise False.
    """
    role = _get_property_role(user, property_obj)
    if role is None:
        return False
    return ROLE_RANK[role] >= ROLE_RANK[min_role]


def _is_client_only_user(user: AuthenticatedUser) -> bool:
    """Return True when user only has client-level shared access.

    Args:
        user: Authenticated request user with a persisted integer id.

    Returns:
        bool: True when the user owns no properties and has no team-level shares.
    """
    if Property.objects.filter(user_id=user.id).exists():
        return False
    if PropertyShare.objects.filter(shared_with_id=user.id, role="team").exists():
        return False
    return PropertyShare.objects.filter(shared_with_id=user.id, role="client").exists()


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect_to_login(request.get_full_path())


def health_check(request: HttpRequest) -> JsonResponse:
    """Return an unauthenticated health payload for platform monitoring."""
    return JsonResponse({"status": "ok"})


@login_required
def dashboard(request):
    if _is_client_only_user(request.user):
        return redirect("property_list")

    from core.services.scoring import score_listing_v2
    from core.models import UserInvestmentTargets

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
    from core.models import UserInvestmentTargets

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
    from core.models import UserInvestmentTargets

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
def property_add(request):
    if _is_client_only_user(request.user):
        return HttpResponseForbidden("Client users have read-only access.")
    if request.method == "POST":
        form = PropertyForm(request.POST)
        if form.is_valid():
            property_obj = form.save(commit=False)
            property_obj.user = request.user
            property_obj.save()
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


def growth_areas(request):
    # Read from GrowthArea model (city/metro-level growth metrics)
    # Fall back to MarketSnapshot for backward compatibility if GrowthArea is empty
    growth_areas_qs = GrowthArea.objects.all()[:200]

    if growth_areas_qs.exists():
        top_growth = sorted(
            growth_areas_qs,
            key=lambda ga: ga.composite_score,
            reverse=True,
        )[:20]
    else:
        # Fallback: use MarketSnapshot (ZIP-level) if GrowthArea not yet populated
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


def _get_financing_value(
    data: Mapping[str, FinancingValue | None], *keys: str
) -> FinancingValue:
    """Return the first non-None value for any provided key in metadata.

    This handles mixed snake_case/camelCase key formats across existing
    financing metadata payloads.
    """
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return None


def _format_financing_value(
    value: FinancingValue, prefix: str = "", suffix: str = ""
) -> str:
    if value is None:
        return "N/A"
    try:
        number = Decimal(str(value))
        return f"{prefix}{number:,.2f}{suffix}"
    except (InvalidOperation, TypeError, ValueError):
        return f"{prefix}{value}{suffix}"


@login_required
def export_pdf(request, pk: int) -> HttpResponse:
    """Render and return a one-page deal summary PDF for an owned property.

    Args:
        request: Authenticated Django request.
        pk: Property primary key.

    Returns:
        HttpResponse: PDF attachment response.

    Raises:
        Http404: If the property is missing or does not belong to the user.
    """
    property_obj = get_object_or_404(
        Property.objects.select_related("analysis").prefetch_related(
            "rental_incomes", "operating_expenses", "transactions"
        ),
        pk=pk,
        user=request.user,
    )
    analysis = getattr(property_obj, "analysis", None)
    rental_income = property_obj.rental_incomes.order_by(
        "-effective_date", "-id"
    ).first()
    default_vacancy_rate = cast(
        Decimal, settings.FINANCE_DEFAULTS.get("vacancy_rate", Decimal("0.05"))
    )
    vacancy_rate: Decimal = (
        rental_income.vacancy_rate
        if rental_income is not None
        else default_vacancy_rate
    )
    effective_gross_income = (
        rental_income.effective_gross_income()
        if rental_income is not None
        else Decimal("0")
    )

    loan_transaction = (
        property_obj.transactions.filter(type=Transaction.Type.LOAN)
        .order_by("-date", "-id")
        .first()
    )
    financing = None
    if loan_transaction:
        metadata = cast(dict[str, FinancingValue | None], loan_transaction.metadata)
        down_payment = _get_financing_value(metadata, "downPayment", "down_payment")
        interest_rate = _get_financing_value(metadata, "interestRate", "interest_rate")
        term_years = _get_financing_value(
            metadata, "loanTermYears", "loan_term_years", "term_years"
        )
        monthly_payment = _get_financing_value(
            metadata, "monthlyPayment", "monthly_payment"
        )
        financing = {
            "down_payment": _format_financing_value(down_payment, "$"),
            "interest_rate": _format_financing_value(interest_rate, suffix="%"),
            "term_years": _format_financing_value(term_years, suffix=" years"),
            "monthly_payment": _format_financing_value(monthly_payment, "$"),
        }
        # Treat fully empty financing payloads as missing data for template display.
        if all(
            value is None
            for value in [down_payment, interest_rate, term_years, monthly_payment]
        ):
            financing = None

    hold_years_default = cast(int, settings.FINANCE_DEFAULTS.get("hold_years", 5))
    exit_cap_rate_default = cast(
        Decimal, settings.FINANCE_DEFAULTS.get("exit_cap_rate", Decimal("0.06"))
    )
    exit_cap_rate_value = analysis.exit_cap_rate if analysis else exit_cap_rate_default

    context = {
        "property": property_obj,
        "property_type": (
            f"Multi-family ({property_obj.units} units)"
            if property_obj.units > 1
            else "Single-family"
        ),
        "analysis": analysis,
        "rental_income": rental_income,
        "effective_gross_income": effective_gross_income,
        "operating_expenses": property_obj.operating_expenses.order_by(
            "category", "id"
        ),
        "financing": financing,
        "assumptions": {
            "vacancy_rate": vacancy_rate,
            "vacancy_rate_pct": vacancy_rate * Decimal("100"),
            "hold_years": analysis.hold_years if analysis else hold_years_default,
            "exit_cap_rate": exit_cap_rate_value,
            "exit_cap_rate_pct": exit_cap_rate_value * Decimal("100"),
        },
        "generated_date": timezone.now(),
    }

    html = render_to_string("exports/deal_summary.html", context)
    pdf_result = BytesIO()
    conversion_result = pisa.CreatePDF(src=html, dest=pdf_result)
    if conversion_result.err:
        logger.error(
            "PDF generation failed for property_id=%s with errors=%s",
            property_obj.pk,
            conversion_result.err,
        )
        return HttpResponse(
            "Unable to generate PDF. Please contact support if this issue persists.",
            status=500,
        )

    filename = f"deal-summary-{slugify(property_obj.address) or property_obj.pk}.pdf"
    response = HttpResponse(pdf_result.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


US_STATES = [
    ("AL", "Alabama"),
    ("AK", "Alaska"),
    ("AZ", "Arizona"),
    ("AR", "Arkansas"),
    ("CA", "California"),
    ("CO", "Colorado"),
    ("CT", "Connecticut"),
    ("DE", "Delaware"),
    ("DC", "District of Columbia"),
    ("FL", "Florida"),
    ("GA", "Georgia"),
    ("HI", "Hawaii"),
    ("ID", "Idaho"),
    ("IL", "Illinois"),
    ("IN", "Indiana"),
    ("IA", "Iowa"),
    ("KS", "Kansas"),
    ("KY", "Kentucky"),
    ("LA", "Louisiana"),
    ("ME", "Maine"),
    ("MD", "Maryland"),
    ("MA", "Massachusetts"),
    ("MI", "Michigan"),
    ("MN", "Minnesota"),
    ("MS", "Mississippi"),
    ("MO", "Missouri"),
    ("MT", "Montana"),
    ("NE", "Nebraska"),
    ("NV", "Nevada"),
    ("NH", "New Hampshire"),
    ("NJ", "New Jersey"),
    ("NM", "New Mexico"),
    ("NY", "New York"),
    ("NC", "North Carolina"),
    ("ND", "North Dakota"),
    ("OH", "Ohio"),
    ("OK", "Oklahoma"),
    ("OR", "Oregon"),
    ("PA", "Pennsylvania"),
    ("RI", "Rhode Island"),
    ("SC", "South Carolina"),
    ("SD", "South Dakota"),
    ("TN", "Tennessee"),
    ("TX", "Texas"),
    ("UT", "Utah"),
    ("VT", "Vermont"),
    ("VA", "Virginia"),
    ("WA", "Washington"),
    ("WV", "West Virginia"),
    ("WI", "Wisconsin"),
    ("WY", "Wyoming"),
]


@login_required
def vrm_properties_list(request: HttpRequest) -> HttpResponse:
    """List VRM properties with state/zip filtering."""
    state = request.GET.get("state", "").strip().upper()
    zip_code = request.GET.get("zip", "").strip()

    queryset = VrmProperty.objects.all()

    if state:
        queryset = queryset.filter(state=state)
    if zip_code:
        queryset = queryset.filter(zip_code=zip_code)

    queryset = queryset.order_by("-last_seen_at")[:100]

    return render(
        request,
        "vrm_properties/list.html",
        {
            "properties": queryset,
            "states": US_STATES,
            "selected_state": state,
            "selected_zip": zip_code,
            "total_count": VrmProperty.objects.count(),
            "filtered_count": queryset.count(),
        },
    )


@login_required
def investment_targets_edit(request: HttpRequest) -> HttpResponse:
    """Edit the current user's investment targets (underwriting thresholds)."""
    targets, _created = UserInvestmentTargets.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = InvestmentTargetsForm(request.POST, instance=targets)
        if form.is_valid():
            form.save()
            return redirect("investment_targets_edit")
    else:
        form = InvestmentTargetsForm(instance=targets)

    return render(
        request,
        "investment_targets/edit.html",
        {"form": form, "targets": targets},
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


def brrrr_calculator(request: HttpRequest) -> HttpResponse:
    """Standalone BRRRR calculator page — no login required.

    Accepts POST with deal inputs and renders the BRRRRAnalysis result.
    GET renders an empty form.
    """
    from decimal import Decimal, InvalidOperation

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
        except (InvalidOperation, ValueError, ZeroDivisionError):
            # Invalid input — render form with no result
            result = None

    return render(
        request,
        "brrrr_calculator.html",
        {"result": result, "form_data": form_data},
    )
