from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseNotAllowed,
    JsonResponse,
)
from django.shortcuts import redirect, render

from core.models import (
    GrowthArea,
    HudProperty,
    UsdaProperty,
    VrmProperty,
)


logger = logging.getLogger(__name__)


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect_to_login(request.get_full_path())


def health_check(request: HttpRequest) -> JsonResponse:
    """Return an unauthenticated health payload for platform monitoring.

    Verifies the database is reachable — Render's healthCheckPath gates
    deploys on this response, so a DB-down instance must not report healthy.
    """
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse(
            {"status": "error", "detail": "database unreachable"}, status=503
        )
    return JsonResponse({"status": "ok"})


@login_required
def system_status(request: HttpRequest) -> HttpResponse:
    """System status page — data inventory and operations (no CLI needed)."""
    from core.models import (
        CountyForeclosureNotice,
        DataSourceHealth,
        PipelineProperty,
    )

    hud_count = HudProperty.objects.count()
    usda_count = UsdaProperty.objects.count()
    vrm_count = VrmProperty.objects.count()
    county_count = CountyForeclosureNotice.objects.count()
    ga_count = GrowthArea.objects.count()
    ga_with_fips = GrowthArea.objects.exclude(county_fips="").count()
    pipeline_count = PipelineProperty.objects.count()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "ingest_hud":
            try:
                from core.services.ingestion import ingest_hud_reo

                result = ingest_hud_reo()
                messages.success(
                    request,
                    f"HUD: {result['created']} loaded, {result['updated']} updated.",
                )
            except Exception as e:
                messages.error(request, f"HUD ingestion failed: {e}")
        elif action == "ingest_usda":
            from core.services.ingestion import ingest_usda_reo

            result = ingest_usda_reo()
            if result.get("error"):
                messages.warning(request, f"USDA: {result['error']}")
            else:
                messages.success(
                    request,
                    f"USDA: {result['created']} loaded, {result['updated']} updated.",
                )
        elif action == "populate_growth":
            import threading

            from django.db import connection as _conn

            TARGET_STATES = ["TX", "FL", "GA", "NC", "AZ", "OH", "IN", "AL", "SC"]

            def _run():
                _conn.close()
                from django.core.management import call_command

                try:
                    call_command(
                        "populate_growth_areas", states=TARGET_STATES, force=True
                    )
                except Exception as e:
                    import logging

                    logging.getLogger("prei.system").error(
                        "Populate growth failed: %s", e
                    )

            t = threading.Thread(target=_run, daemon=True)
            t.start()
            messages.success(
                request,
                f"Growth area analysis started for {len(TARGET_STATES)} states in background. "
                "Refresh in 2-3 minutes to see county-level data.",
            )
        elif action == "sheriff_sales":
            import threading

            from django.db import connection as _conn

            def _run():
                _conn.close()
                from core.services.ingestion import ingest_sheriff_sales

                try:
                    result = ingest_sheriff_sales()
                    logger.info("Sheriff scrape: %d created", result.get("created", 0))
                except Exception as e:
                    logger.error("Sheriff scrape failed: %s", e)

            t = threading.Thread(target=_run, daemon=True)
            t.start()
            messages.success(
                request, "Sheriff sale scrape started for 5 TX counties in background."
            )
        elif action == "scrape_counties":
            import threading

            from django.db import connection as _conn

            def _run():
                _conn.close()
                from core.services.ingestion import ingest_tx_counties

                try:
                    ingest_tx_counties()
                except Exception as e:
                    import logging

                    logging.getLogger("prei.system").error(
                        "County scrape failed: %s", e
                    )

            t = threading.Thread(target=_run, daemon=True)
            t.start()
            messages.success(
                request,
                "County foreclosure scrape started for all 11 TX counties in background.",
            )
        return redirect("system_status")

    return render(
        request,
        "system.html",
        {
            "hud_count": hud_count,
            "hud_states": HudProperty.objects.values("state").distinct().count(),
            "hud_done": hud_count > 0,
            "usda_count": usda_count,
            "usda_states": UsdaProperty.objects.values("state").distinct().count(),
            "usda_done": usda_count > 0,
            "vrm_count": vrm_count,
            "vrm_states": VrmProperty.objects.values("state").distinct().count(),
            "county_count": county_count,
            "ga_count": ga_count,
            "ga_states": GrowthArea.objects.values("state").distinct().count(),
            "ga_fips_pct": f"{ga_with_fips * 100 // max(ga_count, 1)}",
            "pipeline_count": pipeline_count,
            "pipeline_stages": PipelineProperty.objects.values("stage")
            .distinct()
            .count(),
            "health": DataSourceHealth.objects.all(),
            "top_areas": GrowthArea.objects.order_by("-composite_score")[:10],
        },
    )


@login_required
def refresh_all_sources(request: HttpRequest) -> HttpResponse:
    """Trigger all data source refreshes in background threads."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    import threading

    from django.db import connection as _conn

    def _run_ingestion(name, func, *args):
        _conn.close()
        try:
            func(*args)
        except Exception as e:
            logger.error("%s ingestion failed: %s", name, e)

    tasks = [
        (
            "HUD",
            lambda: __import__(
                "core.services.ingestion", fromlist=["ingest_hud_reo"]
            ).ingest_hud_reo(),
        ),
        (
            "USDA",
            lambda: __import__(
                "core.services.ingestion", fromlist=["ingest_usda_reo"]
            ).ingest_usda_reo(),
        ),
        (
            "Counties",
            lambda: __import__(
                "core.services.ingestion", fromlist=["ingest_tx_counties"]
            ).ingest_tx_counties(),
        ),
    ]

    for name, func in tasks:
        t = threading.Thread(target=_run_ingestion, args=(name, func), daemon=True)
        t.start()

    messages.success(
        request, "Refresh started for all data sources. Page will update automatically."
    )
    return redirect("system_status")


@login_required
def health_json(request: HttpRequest) -> HttpResponse:
    """Return data source health as JSON for polling.

    Note: Health data is global (not user-scoped) because data sources
    are shared across all users. The system_status page shows the same
    data to all authenticated users.
    """
    from core.models import DataSourceHealth

    health = list(
        DataSourceHealth.objects.values(
            "source_name", "last_run", "record_count", "status", "consecutive_errors"
        )
    )
    return JsonResponse(health, safe=False)
