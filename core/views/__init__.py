from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from typing import Any

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Q
from django.http import (
    HttpRequest,
    HttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.integrations.market.census import (
    discover_places_in_state,
    fetch_housing_demand_index,
    fetch_place_growth_metrics,
)
from core.integrations.market.market_trends import get_market_health_summary
from core.integrations.sources.fred_adapter import FREDAdapter
from core.models import (
    GrowthArea,
    HudProperty,
    Listing,
    MarketSnapshot,
    PipelineAsset,
    Property,
    SavedSearch,
    UsdaProperty,
    UserInvestmentTargets,
    UserScreeningPreferences,
    VrmProperty,
)
from core.services.audit import log_action

# keep only the models that are actually used
from core.services.cma import estimate_listing_kpis, find_undervalued, price_per_sqft
from core.services.landlord_data import get_state_landlord_score

# Moved from deprecated investor_app.finance.utils:
from core.services.scoring import score_listing
from investor_app.finance.utils import (
    calculate_whatif_monthly_cashflow,
    compute_analysis_for_property,
)

from .constants import US_STATES
from .exports import _generate_pdf as _generate_pdf
from .exports import export_pdf as export_pdf
from .leasing import leasing_add as leasing_add
from .leasing import leasing_application as leasing_application
from .leasing import leasing_detail as leasing_detail
from .leasing import leasing_kanban as leasing_kanban
from .leasing import leasing_lease as leasing_lease
from .leasing import leasing_list as leasing_list
from .leasing import leasing_move_in as leasing_move_in
from .leasing import leasing_screening as leasing_screening
from .leasing import leasing_showing as leasing_showing
from .leasing import leasing_stabilize as leasing_stabilize
from .markets import MarketRefreshView as MarketRefreshView
from .markets import brrrr_calculator as brrrr_calculator
from .markets import investment_targets_edit as investment_targets_edit
from .markets import markets_list as markets_list
from .markets import sell_index as sell_index
from .permissions import _is_client_only_user
from .pipeline import pipeline_add_from_source as pipeline_add_from_source
from .pipeline import pipeline_advance as pipeline_advance
from .pipeline import pipeline_advance_stage as pipeline_advance_stage
from .pipeline import pipeline_closing_create as pipeline_closing_create
from .pipeline import pipeline_dd_checklist as pipeline_dd_checklist
from .pipeline import pipeline_detail as pipeline_detail
from .pipeline import pipeline_hold as pipeline_hold
from .pipeline import pipeline_kanban as pipeline_kanban
from .pipeline import pipeline_kill as pipeline_kill
from .pipeline import pipeline_list as pipeline_list
from .pipeline import pipeline_offer_create as pipeline_offer_create
from .pipeline import pipeline_reactivate as pipeline_reactivate
from .pipeline import pipeline_renovation as pipeline_renovation
from .pipeline import pipeline_review_csv as pipeline_review_csv
from .pipeline import pipeline_review_queue as pipeline_review_queue
from .properties import capex_item_edit as capex_item_edit
from .properties import financing_comparison as financing_comparison
from .properties import property_add as property_add
from .properties import property_add_expense as property_add_expense
from .properties import property_add_income as property_add_income
from .properties import property_compare as property_compare
from .properties import property_delete as property_delete
from .properties import property_detail as property_detail
from .properties import property_edit as property_edit
from .properties import property_list as property_list
from .properties import property_share as property_share
from .screening import pipeline_screener as pipeline_screener
from .screening import pipeline_screening_settings as pipeline_screening_settings
from .screening import screener_filter as screener_filter
from .screening import screening_preview as screening_preview
from .system import health_check as health_check
from .system import health_json as health_json
from .system import home as home
from .system import refresh_all_sources as refresh_all_sources
from .system import system_status as system_status

logger = logging.getLogger(__name__)
User = get_user_model()


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


@login_required
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


@login_required
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
    # Landlord-friendliness tier per state, for the "Tier" selector to narrow
    # the "pick a state" dropdown client-side (JS filters options by data-tier).
    state_tiers = {
        code: get_state_landlord_score(code)["tier"] for code, _ in US_STATES
    }

    if request.method == "GET":
        return render(
            request,
            "growth_explorer.html",
            {
                "states": US_STATES,
                "state_tiers": state_tiers,
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
                "state_tiers": state_tiers,
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
                "state_tiers": state_tiers,
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
                "state_tiers": state_tiers,
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
        # School quality (10% of GACS) — resolved via city→ZIP mapping + GreatSchools API.
        # The mapping covers ~40 major US cities; uncapped cities get None (no penalty).
        school_score = None
        zip_code = None
        try:
            from core.integrations.market.city_zip_map import lookup_city_zip

            zip_code = lookup_city_zip(state, data["place_name"])
        except Exception:
            pass
        if zip_code and data.get("run_school_api", False):
            try:
                from django.conf import settings

                from core.integrations.market.schools import fetch_school_rating

                gs_key = getattr(settings, "GREATSCHOOLS_API_KEY", "")
                school_score = fetch_school_rating(zip_code, gs_key)
            except Exception:
                pass

        # Compute net migration from population data
        from core.models.growth import compute_net_migration

        net_mig, net_mig_rate = compute_net_migration(
            data["population"], data["pop_growth"]
        )

        # Employment: try QCEW county-level on first run, fall back to FRED.
        # On subsequent runs, preserve existing QCEW data.
        from core.data.us_lookup import lookup_county_fips
        from core.integrations.market.qcew_adapter import fetch_county_employment_growth

        city_county_fips = lookup_county_fips(state, data["place_name"])
        existing = GrowthArea.objects.filter(
            state=state, city_name=data["place_name"]
        ).first()

        if existing and existing.employment_growth_rate and existing.county_fips:
            # Already have QCEW data from a prior run — keep it
            emp_rate = existing.employment_growth_rate
            county_fips_to_store = existing.county_fips
        elif city_county_fips:
            # First run — try QCEW county-level (one HTTP call, 5s timeout)
            try:
                qcew = fetch_county_employment_growth(city_county_fips, year=2024)
                if qcew is not None:
                    emp_rate = qcew
                    county_fips_to_store = city_county_fips
                else:
                    emp_rate = safe_emp_growth
                    county_fips_to_store = city_county_fips
            except Exception:
                emp_rate = safe_emp_growth
                county_fips_to_store = city_county_fips
        else:
            emp_rate = safe_emp_growth
            county_fips_to_store = ""

        # FMR data: try on first run, preserve on subsequent runs.
        if existing and existing.fmr_2br is not None:
            rent_growth = existing.rent_growth_rate
            fmr_year = existing.fmr_year
            fmr_2br = existing.fmr_2br
        elif city_county_fips:
            try:
                from core.integrations.market.fmr_adapter import fetch_fmr_data

                fmr_result = fetch_fmr_data(
                    state, city_county_fips, city_name=data["place_name"]
                )
                if fmr_result:
                    rent_growth = fmr_result.get("rent_growth_rate")
                    fmr_year = fmr_result.get("fmr_year")
                    fmr_2br = fmr_result.get("fmr_2br")
                else:
                    rent_growth = fmr_year = fmr_2br = None
            except Exception:
                rent_growth = fmr_year = fmr_2br = None
        else:
            rent_growth = fmr_year = fmr_2br = None

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
                "rent_growth_rate": rent_growth,
                "fmr_year": fmr_year,
                "fmr_2br": fmr_2br,
                "net_migration": net_mig,
                "net_migration_rate": net_mig_rate,
                "county_fips": county_fips_to_store,
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
        from core.services.discovery_processor import process_discovery_batch
        from core.services.screening import ScreeningThresholds, screen_batch
        from core.services.sources.registry import discover_from_all

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
            discovery_result = process_discovery_batch(
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
            screening_result = screen_batch(all_listings, thresholds)

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
            "state_tiers": state_tiers,
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

    items = [{"obj": lst, "score": score_listing(lst)} for lst in qs[:200]]
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


@login_required
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


@login_required
def report_listing(request, listing_id: int):
    try:
        lst = Listing.objects.get(id=listing_id)
    except Listing.DoesNotExist:
        return render(
            request, "property_report.html", {"error": "Listing not found."}, status=404
        )

    score = score_listing(lst)
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


@login_required
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


@login_required
def vrm_properties_list(request: HttpRequest) -> HttpResponse:
    """List VRM properties with state/zip filtering and pipeline integration."""
    state = request.GET.get("state", "").strip().upper()
    zip_code = request.GET.get("zip", "").strip()
    pipeline_message = None

    # Handle pipeline request: run selected properties through discovery
    if request.method == "POST" and "run_pipeline" in request.POST:
        from core.services.screening import ScreeningThresholds, screen_batch

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
            result = screen_batch(payloads, thresholds)
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


def property_discovery(request: HttpRequest) -> HttpResponse:
    """Market-centric property discovery.

    Shows available property sources for a chosen growth area with
    counts of existing records. POST runs discovery for checked sources
    synchronously and adds results to pipeline.

    GET:
      /discovery/                           → redirect to growth_areas
      /discovery/?growth_area_id=42         → market-centric page
      /discovery/?state=TX&city=Austin      → fallback state+city lookup
    POST:
      Runs discovery for checked sources, creates PipelineProperty
      records, and redirects to the screener for this growth area.
    """
    from core.models import (
        CountyForeclosureNotice,
        GrowthArea,
        HudProperty,
        PipelineProperty,
        ScreeningCriteria,
        UsdaProperty,
        VrmProperty,
    )
    from core.services.pipeline import (
        create_from_county_notice,
        create_from_hud,
        create_from_usda,
        create_from_vrm,
    )

    # --- Resolve growth area ---
    growth_area = None
    ga_id = request.GET.get("growth_area_id") or request.POST.get("growth_area_id")
    if ga_id:
        growth_area = get_object_or_404(GrowthArea, pk=ga_id)
    else:
        state = (request.GET.get("state") or request.POST.get("state", "")).upper()
        city = request.GET.get("city") or request.POST.get("city", "")
        if state and city:
            growth_area = GrowthArea.objects.filter(
                state=state, city_name__iexact=city
            ).first()

    if not growth_area:
        # No growth area selected — show the market picker.
        # Lists all available growth areas so the user can choose one
        # without going through the growth_areas list page first.
        user_growth_areas = GrowthArea.objects.order_by("-composite_score")[:50]
        return render(
            request,
            "property_discovery.html",
            {
                "growth_area": None,
                "source_status": [],
                "already_discovered": 0,
                "user_growth_areas": user_growth_areas,
            },
        )

    # --- Available sources with counts ---
    state = growth_area.state
    # Strip Census place-name suffixes (" city", " town", " CDP") for
    # matching against VRM / HUD / USDA data which uses plain city names.
    import re

    city = growth_area.city_name
    city = re.sub(r"\s+(city|town|CDP|village|borough)$", "", city, flags=re.IGNORECASE)

    source_status = [
        {
            "key": "hud",
            "label": "HUD REO",
            "description": "Government-owned HUD foreclosures",
            "count": HudProperty.objects.filter(state=state, city__iexact=city).count(),
            "is_active": True,
        },
        {
            "key": "usda",
            "label": "USDA REO",
            "description": "USDA Rural Development foreclosures",
            "count": UsdaProperty.objects.filter(
                state=state, city__iexact=city
            ).count(),
            "is_active": True,
        },
        {
            "key": "vrm",
            "label": "VRM (VA REO)",
            "description": "VA-owned foreclosures via VRM Properties",
            "count": VrmProperty.objects.filter(state=state, city__iexact=city).count(),
            "is_active": True,
        },
        {
            "key": "attom",
            "label": "ATTOM Pre-foreclosure",
            "description": "NOD/NTS pre-foreclosure notices",
            "count": CountyForeclosureNotice.objects.filter(
                state=state, city__iexact=city
            ).count(),
            "is_active": True,
        },
        {
            "key": "county",
            "label": "County Foreclosure Notices",
            "description": "County-level NTS/auction records",
            "count": CountyForeclosureNotice.objects.filter(
                state=state,
                city__iexact=city,
                document_type__in=["nts", "sheriff_sale", "auction"],
            ).count(),
            "is_active": True,
        },
    ]

    # Already-discovered count for this growth area
    already_discovered = PipelineProperty.objects.filter(
        user=request.user,
        growth_area=growth_area,
    ).count()

    # --- GET: show discovery form ---
    if request.method == "GET":
        return render(
            request,
            "property_discovery.html",
            {
                "growth_area": growth_area,
                "source_status": source_status,
                "already_discovered": already_discovered,
            },
        )

    # --- POST: run discovery ---
    selected_sources = request.POST.getlist("sources")
    if not selected_sources:
        messages.warning(request, "Please select at least one source.")
        return redirect(f"{request.path}?growth_area_id={growth_area.pk}")

    # Trigger source data collection when needed.
    # All collection runs in background threads — Gunicorn worker timeout = 30s.
    if "vrm" in selected_sources:
        vrm_count = VrmProperty.objects.filter(state=state).count()
        if vrm_count == 0:
            import threading

            from django.db import connection as _conn

            def _scrape_vrm(state_code: str) -> None:
                _conn.close()
                from core.integrations.sources.vrm_scraper import VrmScraper

                scraper = VrmScraper()
                listings = scraper.collect_state_listings(state_code)
                now = timezone.now()
                for listing in listings:
                    listing["scraped_at"] = now
                    listing["last_seen_at"] = now
                    try:
                        VrmProperty.objects.update_or_create(
                            vrm_property_id=listing["vrm_property_id"],
                            defaults=listing,
                        )
                    except Exception as exc:
                        logger.error(
                            "Background VRM scrape: failed to save listing %s: %s",
                            listing.get("vrm_property_id"),
                            exc,
                        )

            t = threading.Thread(target=_scrape_vrm, args=(state,), daemon=True)
            t.start()
            messages.info(
                request,
                f"VRM scrape for {state} started in background. "
                "Refresh the page in a minute to see results.",
            )

    if "hud" in selected_sources:
        hud_count = HudProperty.objects.count()
        if hud_count == 0:
            try:
                import time

                from django.db import OperationalError

                from core.services.ingestion import ingest_hud_reo

                for attempt in range(3):
                    try:
                        result = ingest_hud_reo()
                        break
                    except OperationalError as e:
                        if "locked" in str(e) and attempt < 2:
                            time.sleep(0.5 * (attempt + 1))
                            continue
                        raise
                messages.info(
                    request,
                    f"HUD data loaded: {result['created']} properties indexed nationwide. "
                    f"Run discovery again to find properties in this market.",
                )
            except Exception as exc:
                logger.error("Discovery HUD ingestion failed: %s", exc)
                messages.warning(request, "HUD data download failed. Try again later.")

    if "usda" in selected_sources:
        usda_count = UsdaProperty.objects.count()
        if usda_count == 0:
            try:
                import time as _t

                from django.db import OperationalError as _oe

                from core.services.ingestion import ingest_usda_reo

                for _a in range(3):
                    try:
                        result = ingest_usda_reo()
                        break
                    except _oe as e:
                        if "locked" in str(e) and _a < 2:
                            _t.sleep(0.5 * (_a + 1))
                            continue
                        raise
                if result.get("created", 0) > 0:
                    messages.info(
                        request, f"USDA data loaded: {result['created']} properties."
                    )
                else:
                    messages.info(
                        request,
                        "USDA data not yet available. Use manage.py ingest_usda_reo.",
                    )
            except Exception as exc:
                logger.error("Discovery USDA ingestion failed: %s", exc)

    # Get or create user screening criteria for auto-screening
    try:
        criteria = ScreeningCriteria.objects.get(user=request.user)
    except ScreeningCriteria.DoesNotExist:
        criteria = None

    results = {
        "discovered": 0,
        "already_existed": 0,
        "screening_passed": 0,
        "screening_failed": 0,
        "sources_attempted": [],
        "errors": [],
        "properties": [],
    }

    # --- HUD ---
    if "hud" in selected_sources:
        results["sources_attempted"].append("HUD")
        try:
            hud_qs = HudProperty.objects.filter(
                state=state,
                city__iexact=city,
                status="active",
            )
            for hud in hud_qs:
                pp, created = create_from_hud(
                    hud, request.user, growth_area=growth_area
                )
                if created:
                    results["discovered"] += 1
                    results["properties"].append(pp)
                    if criteria and pp.screening_passed is not None:
                        if pp.screening_passed:
                            results["screening_passed"] += 1
                        else:
                            results["screening_failed"] += 1
                else:
                    results["already_existed"] += 1
        except Exception as exc:
            logger.error("Discovery HUD error for %s: %s", city, exc)
            results["errors"].append(f"HUD: {exc}")

    # --- USDA ---
    if "usda" in selected_sources:
        results["sources_attempted"].append("USDA")
        try:
            usda_qs = UsdaProperty.objects.filter(
                state=state,
                city__iexact=city,
                status="active",
            )
            for usda in usda_qs:
                pp, created = create_from_usda(
                    usda, request.user, growth_area=growth_area
                )
                if created:
                    results["discovered"] += 1
                    results["properties"].append(pp)
                    if criteria and pp.screening_passed is not None:
                        if pp.screening_passed:
                            results["screening_passed"] += 1
                        else:
                            results["screening_failed"] += 1
                else:
                    results["already_existed"] += 1
        except Exception as exc:
            logger.error("Discovery USDA error for %s: %s", city, exc)
            results["errors"].append(f"USDA: {exc}")

    # --- VRM ---
    if "vrm" in selected_sources:
        results["sources_attempted"].append("VRM")
        try:
            vrm_qs = VrmProperty.objects.filter(
                state=state,
                city__iexact=city,
                status="for_sale",
            )
            for vrm in vrm_qs:
                pp, created = create_from_vrm(
                    vrm, request.user, growth_area=growth_area
                )
                if created:
                    results["discovered"] += 1
                    results["properties"].append(pp)
                    if criteria and pp.screening_passed is not None:
                        if pp.screening_passed:
                            results["screening_passed"] += 1
                        else:
                            results["screening_failed"] += 1
                else:
                    results["already_existed"] += 1
        except Exception as exc:
            logger.error("Discovery VRM error for %s: %s", city, exc)
            results["errors"].append(f"VRM: {exc}")

    # --- ATTOM + County (both use CountyForeclosureNotice) ---
    if "attom" in selected_sources or "county" in selected_sources:
        results["sources_attempted"].append("Foreclosures")
        try:
            notice_qs = CountyForeclosureNotice.objects.filter(
                state=state,
                city__iexact=city,
            )
            for notice in notice_qs:
                pp, created = create_from_county_notice(
                    notice, request.user, growth_area=growth_area
                )
                if created:
                    results["discovered"] += 1
                    results["properties"].append(pp)
                    if criteria and pp.screening_passed is not None:
                        if pp.screening_passed:
                            results["screening_passed"] += 1
                        else:
                            results["screening_failed"] += 1
                else:
                    results["already_existed"] += 1
        except Exception as exc:
            logger.error("Discovery foreclosure error for %s: %s", city, exc)
            results["errors"].append(f"Foreclosure: {exc}")

    # Show results in-page instead of redirecting to screener.
    # User sees exactly what was found per source without losing context.
    return render(
        request,
        "property_discovery.html",
        {
            "growth_area": growth_area,
            "source_status": source_status,
            "already_discovered": PipelineProperty.objects.filter(
                user=request.user, growth_area=growth_area
            ).count(),
            "discovery_results": results,
            "show_results": True,
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
