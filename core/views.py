from __future__ import annotations

import logging
from io import BytesIO
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Protocol, cast

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db.models import Avg, Q, Sum
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
from xhtml2pdf import pisa

from investor_app.finance.utils import (
    compute_analysis_for_property,
    calculate_whatif_monthly_cashflow,
    score_listing_v1,
)

# keep only the models that are actually used
from core.services.cma import estimate_listing_kpis, find_undervalued, price_per_sqft
from core.services.audit import log_action
from .forms import OperatingExpenseForm, PropertyForm, RentalIncomeForm
from .models import (
    InvestmentAnalysis,
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


def _portfolio_summary(user: AuthenticatedUser) -> dict[str, Decimal | int]:
    """Compute portfolio-level summary metrics for the given authenticated user.

    Args:
        user: Authenticated request user with a persisted integer id.

    Returns:
        dict[str, Decimal | int]: Total property count, invested capital, and
        average cap rate for owner-scoped properties.
    """
    properties = Property.objects.filter(user_id=user.id)
    total_invested = properties.aggregate(total=Sum("purchase_price"))[
        "total"
    ] or Decimal("0")
    average_cap_rate = InvestmentAnalysis.objects.filter(
        property__user_id=user.id
    ).aggregate(average=Avg("cap_rate"))["average"] or Decimal("0")
    return {
        "total_properties": properties.count(),
        "total_invested": total_invested,
        "average_cap_rate": average_cap_rate,
    }


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
    for property_obj in properties:
        property_obj.access_role = (
            "owner"
            if property_obj.user_id == request.user.id
            else share_roles_by_property_id.get(property_obj.id, "client")
        )

    return render(
        request,
        "properties/list.html",
        {
            "properties": properties,
            "portfolio_summary": _portfolio_summary(request.user),
            "can_add_property": not _is_client_only_user(request.user),
        },
    )


def _parse_compare_ids(raw_ids: list[str]) -> tuple[list[int], str | None]:
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

    seen_ids: set[int] = set()
    unique_ids: list[int] = []
    for property_id in parsed_ids:
        if property_id not in seen_ids:
            seen_ids.add(property_id)
            unique_ids.append(property_id)

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
        raise Http404

    ordered_properties = [properties_by_id[property_id] for property_id in unique_ids]
    property_data: list[dict[str, object]] = []
    for property_obj in ordered_properties:
        analysis = getattr(property_obj, "analysis", None)
        if analysis is None:
            analysis = compute_analysis_for_property(property_obj)
        rental_income = property_obj.rental_incomes.order_by(
            "-effective_date", "-id"
        ).first()
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
    return render(
        request,
        "properties/detail.html",
        {
            "property": property_obj,
            "analysis": getattr(property_obj, "analysis", None),
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
            return redirect("property_add_income", pk=property_obj.pk)
    else:
        form = PropertyForm()

    return render(request, "properties/add.html", {"form": form})


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
        "properties/edit.html",
        {
            "form": form,
            "property": property_obj,
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
