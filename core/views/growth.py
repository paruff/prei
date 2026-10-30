from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, Paginator
from django.http import (
    HttpRequest,
    HttpResponse,
)
from django.shortcuts import render
from django.utils import timezone

from core.integrations.market.census import (
    discover_places_in_state,
    fetch_housing_demand_index,
    fetch_place_growth_metrics,
)
from core.integrations.sources.fred_adapter import FREDAdapter
from core.models import (
    GrowthArea,
    Listing,
    MarketSnapshot,
    UserScreeningPreferences,
)

from core.services.cma import find_undervalued
from core.services.landlord_data import get_state_landlord_score
from .constants import US_STATES


logger = logging.getLogger(__name__)


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
