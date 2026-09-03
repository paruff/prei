from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpRequest,
    HttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.models import (
    GrowthArea,
    HudProperty,
    Listing,
    MarketSnapshot,
    Property,
    SavedSearch,
    UsdaProperty,
    VrmProperty,
)
from core.services.audit import log_action

from core.services.cma import estimate_listing_kpis, price_per_sqft

from core.services.scoring import score_listing
from investor_app.finance.utils import (
    calculate_whatif_monthly_cashflow,
    compute_analysis_for_property,
)

from .constants import US_STATES

logger = logging.getLogger(__name__)
User = get_user_model()


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
