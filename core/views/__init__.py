from __future__ import annotations

import io
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol, cast

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import EmptyPage, Paginator
from django.db.models import F, Q, Count
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
from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

from core.integrations.market.census import (
    discover_places_in_state,
    fetch_housing_demand_index,
    fetch_place_growth_metrics,
)
from core.integrations.sources.fred_adapter import FREDAdapter

from core.models import (
    HudProperty,
    UsdaProperty,
    VrmProperty,
    UserInvestmentTargets,
    GrowthArea,
    PipelineAsset,
    UserScreeningPreferences,
)

from prei.integrations.landlord_data import get_state_landlord_score
from investor_app.finance.utils import (
    compute_analysis_for_property,
    calculate_whatif_monthly_cashflow,
    score_listing_v1,
)

# keep only the models that are actually used
from core.services.cma import estimate_listing_kpis, find_undervalued, price_per_sqft
from core.services import compute_portfolio_summary
from core.services.audit import log_action
from core.forms import (
    OperatingExpenseForm,
    PropertyForm,
    RentalIncomeForm,
    InvestmentTargetsForm,
)
from core.models import (
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
    """Display paginated growth areas sorted by composite score.

    Supports GET parameters:
        page: Page number (default 1)
    """
    page = request.GET.get("page", 1)
    try:
        page = int(page)
    except ValueError, TypeError:
        page = 1

    growth_areas_qs = GrowthArea.objects.all().order_by("-composite_score")

    if growth_areas_qs.exists():
        paginator = Paginator(growth_areas_qs, 25)
        try:
            growth_page = paginator.page(page)
        except EmptyPage:
            growth_page = paginator.page(paginator.num_pages)
        data_source = "growtharea"
    else:
        # Fallback: use MarketSnapshot (ZIP-level) if GrowthArea not yet populated
        snapshots = MarketSnapshot.objects.all().order_by("-price_trend")[:50]
        growth_page = snapshots
        data_source = "snapshot"

    # Flag undervalued listings globally as a placeholder
    undervalued = find_undervalued(Listing.objects.all()[:200])
    return render(
        request,
        "growth_areas.html",
        {
            "growth_page": growth_page,
            "data_source": data_source,
            "undervalued": undervalued,
        },
    )


def growth_areas_export_csv(request: HttpRequest) -> HttpResponse:
    """Export all GrowthArea data as CSV."""
    import csv

    queryset = GrowthArea.objects.all().order_by("-composite_score")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="growth-areas-{timezone.now().strftime("%Y%m%d")}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(
        [
            "State",
            "City",
            "Population",
            "Pop Growth (%)",
            "Emp Growth (%)",
            "Income Growth (%)",
            "Housing Demand",
            "Supply Constraint",
            "Composite Score",
            "Data Timestamp",
        ]
    )
    for ga in queryset:
        writer.writerow(
            [
                ga.state,
                ga.city_name,
                ga.population or "",
                f"{float(ga.population_growth_rate or 0) * 100:.2f}",
                f"{float(ga.employment_growth_rate or 0) * 100:.2f}",
                f"{float(ga.median_income_growth or 0) * 100:.2f}",
                ga.housing_demand_index or "",
                ga.supply_constraint_index or "",
                f"{float(ga.composite_score or 0):.2f}",
                ga.data_timestamp.strftime("%Y-%m-%d %H:%M")
                if ga.data_timestamp
                else "",
            ]
        )

    return response


def growth_explorer(request: HttpRequest) -> HttpResponse:
    """Growth Area Explorer — discover and analyze top growth places in a state.

    Synchronous flow (matches VRM scrape pattern):
    1. GET: render state picker form
    2. POST: call discover_places_in_state (limit=10), fetch_employment_growth (once),
       then for each place: fetch_place_growth_metrics + fetch_housing_demand_index,
       upsert into GrowthArea, render results sorted by composite_score.
    """
    from os import getenv

    census_api_key = getenv("CENSUS_API_KEY", "")
    census_configured = bool(census_api_key)
    # FRED key is optional — if missing, employment growth defaults to 0
    fred_key = getenv("FRED_API_KEY") or getenv("FRED_api_key") or ""
    fred_configured = bool(fred_key)
    api_keys_configured = bool(census_api_key)

    if request.method == "GET":
        return render(
            request,
            "growth_explorer.html",
            {
                "states": US_STATES,
                "api_keys_configured": api_keys_configured,
                "census_key_configured": census_configured,
                "fred_key_configured": fred_configured,
            },
        )

    # POST — synchronous analysis
    if not api_keys_configured:
        return render(
            request,
            "growth_explorer.html",
            {
                "states": US_STATES,
                "api_keys_configured": False,
                "census_key_configured": bool(census_api_key),
                "fred_key_configured": fred_configured,
                "error": "CENSUS_API_KEY not configured. Set CENSUS_API_KEY in your environment.",
            },
        )

    state = request.POST.get("state", "").strip().upper()
    if not state or state not in [s[0] for s in US_STATES]:
        return render(
            request,
            "growth_explorer.html",
            {
                "states": US_STATES,
                "api_keys_configured": api_keys_configured,
                "census_key_configured": bool(census_api_key),
                "fred_key_configured": fred_configured,
                "error": "Invalid state selected.",
            },
        )

    # 1. Discover top 10 places in state by population
    logger.info("Growth Explorer: discovering places in state %s", state)
    places = discover_places_in_state(state, census_api_key, limit=10)
    if not places:
        logger.warning("Growth Explorer: no places found for state %s", state)
        error_msg = (
            f"No Census data returned for {state}. "
            "This usually means: <br>"
            "1. <strong>CENSUS_API_KEY</strong> is missing or invalid — "
            "<a href='https://api.census.gov/data/key_signup.html' target='_blank' rel='noopener'>get a free key</a>"
            "<br>2. The Census API is temporarily unavailable (try again later)"
        )
        return render(
            request,
            "growth_explorer.html",
            {
                "states": US_STATES,
                "api_keys_configured": api_keys_configured,
                "census_key_configured": bool(census_api_key),
                "fred_key_configured": fred_configured,
                "error": error_msg,
            },
        )

    logger.info("Growth Explorer: discovered %d places in state %s", len(places), state)

    # 2. Fetch state-level employment growth via FRED (no rate limit issues like BLS)
    logger.info("Growth Explorer: fetching state-level employment growth for %s", state)
    fred = FREDAdapter()
    emp_growth = fred.fetch_state_employment_growth(state)

    # 3. For each place, fetch Census place metrics + housing demand (parallel API calls)
    safe_emp_growth = emp_growth if emp_growth is not None else Decimal("0")

    def _fetch_place_data(place: dict) -> dict | None:
        """Fetch Census data for a single place. API calls only — no DB writes."""
        place_code = place["place_code"]
        place_name = place["place_name"]
        population = place["population"]

        census_data = fetch_place_growth_metrics(state, place_code, census_api_key)
        if census_data is None:
            return None

        pop_growth = census_data.get("population_growth_rate")
        income_growth = census_data.get("median_income_growth_rate")
        if pop_growth is None:
            pop_growth = Decimal("0")
        if income_growth is None:
            income_growth = Decimal("0")

        housing_demand = fetch_housing_demand_index(
            state_code=state,
            place_code=place_code,
            api_key=census_api_key,
            population_growth_rate=pop_growth,
        )
        if housing_demand is None:
            housing_demand = 50

        return {
            "place_code": place_code,
            "place_name": place_name,
            "population": population,
            "pop_growth": pop_growth,
            "income_growth": income_growth,
            "housing_demand": housing_demand,
        }

    logger.info(
        "Growth Explorer: fetching Census data for %d places in parallel for %s",
        len(places),
        state,
    )
    place_data_list: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(len(places), 10)) as executor:
        futures = {executor.submit(_fetch_place_data, p): p for p in places}
        for future in as_completed(futures):
            try:
                result = future.result()
                if result is not None:
                    place_data_list.append(result)
            except Exception as exc:
                logger.error("Growth Explorer: parallel fetch failed: %s", exc)

    # 4a. Upsert GrowthArea rows sequentially (SQLite does not support concurrent writes)
    results = []
    for data in place_data_list:
        # School quality (15% of GACS) is not populated during explorer runs because
        # _fetch_place_data does not return a ZIP code.  School scores can be set
        # manually via the admin or via a future batch enrichment command that
        # resolves city→ZIP→GreatSchools rating.
        # See core/integrations/market/schools.py for the fetch_school_rating adapter.
        school_score = None

        # Compute net migration from population data
        from core.models.growth import compute_net_migration

        net_mig, net_mig_rate = compute_net_migration(
            data["population"], data["pop_growth"]
        )

        # Attempt county-level employment via QCEW (replaces FRED when county is known)
        from core.integrations.market.county_fips_map import lookup_county_fips
        from core.integrations.market.qcew_adapter import fetch_county_employment_growth

        emp_rate = safe_emp_growth
        county_fips = lookup_county_fips(state, data["place_name"])
        if county_fips:
            qcew_growth = fetch_county_employment_growth(county_fips, year=2024)
            if qcew_growth is not None:
                emp_rate = qcew_growth

        growth_area, _ = GrowthArea.objects.update_or_create(
            state=state,
            city_name=data["place_name"],
            defaults={
                "metro_area": "",
                "population": data["population"],
                "population_growth_rate": data["pop_growth"],
                "employment_growth_rate": emp_rate,
                "median_income_growth": data["income_growth"],
                "housing_demand_index": data["housing_demand"],
                "school_score": school_score,
                "net_migration": net_mig,
                "net_migration_rate": net_mig_rate,
                "county_fips": county_fips or "",
                "landlord_score": get_state_landlord_score(state)["score"],
                "data_timestamp": timezone.now(),
            },
        )
        results.append(
            {
                "growth_area": growth_area,
                "place_name": data["place_name"],
                "population": data["population"],
            }
        )

    # 5. Sort by composite_score descending (None scores sort last)
    results.sort(
        key=lambda r: r["growth_area"].composite_score or Decimal("-999"),
        reverse=True,
    )

    # Add landlord-friendliness info to each result
    state_info = get_state_landlord_score(state)
    for r in results:
        r["landlord_score"] = state_info["score"]
        r["landlord_label"] = state_info["label"]
        r["landlord_tier"] = state_info["tier"]

    # 6. Optional: pipeline discovery for a specific city
    pipeline_results = None
    pipeline_city = request.POST.get("pipeline_city", "").strip()
    if pipeline_city:
        from prei.pipeline.handlers.discovery_processor import DiscoveryProcessor
        from prei.pipeline.handlers.screening import ScreeningThresholds
        from prei.pipeline.handlers.batch_screening import BatchScreeningProcessor
        from prei.pipeline.engine import InMemoryAssetRepository, PipelineEngine
        from prei.pipeline.sources.registry import discover_from_all

        logger.info(
            "Growth Explorer: running pipeline discovery for %s, %s",
            pipeline_city,
            state,
        )
        try:
            # Discover raw listings from available sources
            source_results = discover_from_all(state=state)
            all_listings: list[dict] = []
            for src_name, listings in source_results.items():
                for listing in listings:
                    listing["source"] = src_name
                    all_listings.append(listing)

            # Run through discovery processor (dedup + state inception)
            processor = DiscoveryProcessor(existing_hashes=set())
            discovery_result = processor.process_batch(
                all_listings, source_name="growth_explorer"
            )

            # Run through batch screening with user preferences when available
            min_yield = Decimal("0.07")
            max_ptr = Decimal("15.0")
            min_beds = 1
            min_baths = 1
            if request.user.is_authenticated:
                try:
                    prefs = UserScreeningPreferences.objects.get(user=request.user)
                    min_yield = prefs.min_gross_yield
                    max_ptr = prefs.max_price_to_rent_ratio
                    min_beds = prefs.min_beds
                    min_baths = prefs.min_baths
                except UserScreeningPreferences.DoesNotExist:
                    pass

            thresholds = ScreeningThresholds(
                min_gross_yield=float(min_yield),
                max_price_to_rent_ratio=float(max_ptr),
                min_beds=min_beds,
                min_baths=min_baths,
            )
            engine = PipelineEngine(repository=InMemoryAssetRepository())
            batch_processor = BatchScreeningProcessor(engine, thresholds)
            screening_result = batch_processor.process(all_listings)

            pipeline_results = {
                "city": pipeline_city,
                "sources_queried": list(source_results.keys()),
                "total_discovered": discovery_result["new_assets_discovered"],
                "duplicates": discovery_result["duplicates_skipped"],
                "failed": discovery_result["failed_records"],
                "passed_screening": screening_result["advanced"],
                "failed_screening": screening_result["killed"],
                "skipped_total": discovery_result["duplicates_skipped"]
                + discovery_result["failed_records"],
                "execution_ms": round(screening_result["execution_time_ms"], 0),
            }
        except Exception as exc:
            logger.error(
                "Growth Explorer: pipeline discovery failed for %s, %s: %s",
                pipeline_city,
                state,
                exc,
            )
            pipeline_results = {"error": str(exc), "city": pipeline_city}

    return render(
        request,
        "growth_explorer.html",
        {
            "states": US_STATES,
            "selected_state": state,
            "results": results,
            "emp_growth": emp_growth,
            "pipeline_results": pipeline_results,
            "fred_key_configured": fred_configured,
            "census_key_configured": bool(census_api_key),
            "api_keys_configured": bool(census_api_key),
        },
    )


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
    from core.models import GrowthArea, PipelineProperty

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
    stage_counts: dict[str, int] = {}
    for pp in stage_qs:
        stage_counts[pp.stage] = stage_counts.get(pp.stage, 0) + 1

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

    if action == "hold":
        prop.status = PipelineProperty.Status.ON_HOLD
        prop.save(update_fields=["status", "updated_at"])
        messages.info(request, f"{prop.address} has been moved to Hold.")
    else:
        messages.warning(request, f"Unknown action: {action}")

    return redirect("pipeline_review_queue")


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

        # Re-screen all ACTIVE pipeline properties at DISCOVERED or SCREENING
        rescreen_count = 0
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


@login_required
def leasing_list(request: HttpRequest) -> HttpResponse:
    """List leasing pipeline entries for the current user."""
    from core.models import LeasingPipelineProperty
    from datetime import date

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
def leasing_add(request: HttpRequest) -> HttpResponse:
    """Add a new leasing pipeline entry."""
    from core.models import LeasingPipelineProperty, Property

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
        except SavedSearch.DoesNotExist, ValueError:
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
    except InvalidOperation, TypeError, ValueError:
        return f"{prefix}{value}{suffix}"


def _generate_pdf(html: str) -> bytes:
    """Generate a PDF from HTML content using Playwright.

    Uses headless Chromium (already a project dependency) to render
    the HTML template and produce a PDF.  This replaces the prior
    xhtml2pdf approach which was incompatible with reportlab>=5.
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            pdf_bytes: bytes = page.pdf(format="A4", print_background=True)
            return pdf_bytes
        finally:
            browser.close()


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

    try:
        pdf_bytes = _generate_pdf(html)
    except Exception as exc:
        logger.error(
            "PDF generation failed for property_id=%s: %s",
            property_obj.pk,
            exc,
        )
        return HttpResponse(
            "Unable to generate PDF. Please contact support if this issue persists.",
            status=500,
        )

    filename = f"deal-summary-{slugify(property_obj.address) or property_obj.pk}.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
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
    """List VRM properties with state/zip filtering and pipeline integration."""
    state = request.GET.get("state", "").strip().upper()
    zip_code = request.GET.get("zip", "").strip()
    pipeline_message = None

    # Handle pipeline request: run selected properties through discovery
    if request.method == "POST" and "run_pipeline" in request.POST:
        from prei.pipeline.engine import InMemoryAssetRepository, PipelineEngine
        from prei.pipeline.handlers.screening import ScreeningThresholds
        from prei.pipeline.handlers.batch_screening import BatchScreeningProcessor

        prop_ids = request.POST.getlist("pipeline_props")
        if prop_ids:
            properties = VrmProperty.objects.filter(
                vrm_property_id__in=[int(p) for p in prop_ids]
            )
            payloads = []
            for prop in properties:
                payloads.append(
                    {
                        "asset_id": f"vrm-{prop.vrm_property_id}",
                        "address": f"{prop.address}, {prop.city}, {prop.state} {prop.zip_code}",
                        "price": float(prop.list_price) if prop.list_price else None,
                        "rent": float(prop.projected_monthly_rent)
                        if prop.projected_monthly_rent
                        else None,
                    }
                )

            thresholds = ScreeningThresholds(
                min_gross_yield=0.07,
                max_price_to_rent_ratio=15.0,
                min_beds=1,
                min_baths=1,
            )
            engine = PipelineEngine(repository=InMemoryAssetRepository())
            processor = BatchScreeningProcessor(engine, thresholds)
            result = processor.process(payloads)
            pipeline_message = (
                f"{len(payloads)} properties processed: "
                f"{result['advanced']} passed screening, "
                f"{result['killed']} rejected."
            )

    queryset = VrmProperty.objects.all()
    if state:
        queryset = queryset.filter(state=state)
    if zip_code:
        queryset = queryset.filter(zip_code=zip_code)
    queryset = queryset.order_by("-last_seen_at")[:100]

    # Annotate with pipeline membership (dict: source_id → pipeline_pk)
    from core.models import PipelineProperty

    if request.user.is_authenticated:
        user_pipeline_entries = {
            str(pp.source_id): pp.pk
            for pp in PipelineProperty.objects.filter(
                user=request.user, source_type=PipelineProperty.SourceType.VRM
            )
        }
    else:
        user_pipeline_entries = {}

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
            "pipeline_message": pipeline_message,
            "pipeline_entries": user_pipeline_entries,
        },
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
        except InvalidOperation, ValueError, ZeroDivisionError:
            # Invalid input — render form with no result
            result = None

    return render(
        request,
        "brrrr_calculator.html",
        {"result": result, "form_data": form_data},
    )


def sell_index(request: HttpRequest) -> HttpResponse:
    """Sell/Disposition stub page — placeholder for future disposition tools."""
    return render(request, "sell_index.html")


def property_discovery(request: HttpRequest) -> HttpResponse:
    """Property Discovery page — browse sources and request property feeds.

    Shows all available ``PropertySource`` records grouped by type,
    along with the current user's recent ``DiscoveryRequest`` submissions.
    Users can submit new requests to be fulfilled by future scrapers.
    """
    from core.models import DiscoveryRequest, PropertySource

    # Handle new discovery request
    if request.method == "POST" and "request_discovery" in request.POST:
        source_id = request.POST.get("source_id", "")
        location = request.POST.get("location", "").strip()
        if source_id and location:
            DiscoveryRequest.objects.create(
                user=request.user,
                source_id=source_id,
                location=location,
            )

    sources = PropertySource.objects.all()
    user_requests = DiscoveryRequest.objects.filter(user=request.user)[:20]

    # Group sources
    free_sources = sources.filter(is_free=True)
    paid_sources = sources.filter(is_free=False)
    active_sources = sources.filter(is_active=True)
    planned_sources = sources.filter(is_active=False)

    return render(
        request,
        "property_discovery.html",
        {
            "sources": sources,
            "free_sources": free_sources,
            "paid_sources": paid_sources,
            "active_sources": active_sources,
            "planned_sources": planned_sources,
            "user_requests": user_requests,
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HUD Property Views
# ═══════════════════════════════════════════════════════════════════════════════


def hud_property_list(request: HttpRequest) -> HttpResponse:
    """List HUD properties with optional state filter."""
    state = request.GET.get("state", "").strip().upper()

    queryset = HudProperty.objects.all().order_by("-created_at")
    if state:
        queryset = queryset.filter(state=state)

    context: dict[str, Any] = {
        "hud_properties": queryset,
        "selected_state": state,
        "total_count": HudProperty.objects.count(),
        "filtered_count": queryset.count(),
    }
    return render(request, "hud_properties/list.html", context)


def hud_property_detail(
    request: HttpRequest,
    pk: int,
) -> HttpResponse:
    """Detail view for a single HUD property with Add to Pipeline button."""
    hud_property = get_object_or_404(HudProperty, pk=pk)

    context: dict[str, Any] = {
        "hud_property": hud_property,
    }
    return render(request, "hud_properties/detail.html", context)


# ═══════════════════════════════════════════════════════════════════════════════
# USDA Property Views
# ═══════════════════════════════════════════════════════════════════════════════


def usda_property_list(request: HttpRequest) -> HttpResponse:
    """List USDA properties with optional state filter."""
    state = request.GET.get("state", "").strip().upper()

    queryset = UsdaProperty.objects.all().order_by("-created_at")
    if state:
        queryset = queryset.filter(state=state)

    context: dict[str, Any] = {
        "usda_properties": queryset,
        "selected_state": state,
        "total_count": UsdaProperty.objects.count(),
        "filtered_count": queryset.count(),
    }
    return render(request, "usda_properties/list.html", context)


def usda_property_detail(
    request: HttpRequest,
    pk: int,
) -> HttpResponse:
    """Detail view for a single USDA property with Add to Pipeline button."""
    usda_property = get_object_or_404(UsdaProperty, pk=pk)

    context: dict[str, Any] = {
        "usda_property": usda_property,
    }
    return render(request, "usda_properties/detail.html", context)
