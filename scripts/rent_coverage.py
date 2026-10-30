"""Rent coverage by source on the seeded market (NFR-7, AC-13). Prints Markdown.

Run in the container (after `make docker-seed`):
    make docker-rent-report SEED_ARGS="--city Dallas --state TX"
or: python scripts/rent_coverage.py --city Dallas --state TX

Sources: VRM projected rent (stored), HUD FMR (county, by bedrooms), Rentcast
(only when RENTCAST_API_KEY is set). Rentometer has no adapter, so it is not measured.
"""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal
from statistics import median

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "investor_app.settings")
django.setup()

from django.conf import settings  # noqa: E402

from core.integrations.market.hud_fmr import get_rent_estimate  # noqa: E402
from core.integrations.market.rents import fetch_rent_estimate  # noqa: E402
from core.models import GrowthArea, VrmProperty  # noqa: E402

RENTCAST_SAMPLE = 25  # free tier is 100 calls/day; keep a margin


def pct(n: int, total: int) -> str:
    return f"{n}/{total} ({100 * n / total:.0f}%)" if total else "0/0"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default="Dallas")
    ap.add_argument("--state", default="TX")
    args = ap.parse_args()
    state, city = args.state.upper(), args.city.title()

    area = GrowthArea.objects.filter(state=state, city_name=city).first()
    props = list(VrmProperty.objects.filter(state=state, city__iexact=city))
    if area is None or not props:
        print(
            f"No seeded market for {city}, {state}: run seed_market first.",
            file=sys.stderr,
        )
        return 1

    fips = area.county_fips
    hud: dict[int, Decimal | None] = {}
    for p in props:
        beds = p.bedrooms or 2
        if beds not in hud:
            hud[beds] = get_rent_estimate(fips_code=fips, bedrooms=beds)

    key = getattr(settings, "RENTCAST_API_KEY", "") or os.environ.get(
        "RENTCAST_API_KEY", ""
    )
    pairs: list[tuple[Decimal, Decimal]] = []  # (hud, rentcast)
    rc_hits = rc_tried = 0
    if key:
        for p in props[:RENTCAST_SAMPLE]:
            rc_tried += 1
            rc = fetch_rent_estimate(
                f"{p.address}, {p.city}, {p.state}", key, p.zip_code
            )
            h = hud.get(p.bedrooms or 2)
            if rc:
                rc_hits += 1
                if h:
                    pairs.append((h, rc))

    n = len(props)
    vrm_n = sum(1 for p in props if p.projected_monthly_rent)
    hud_n = sum(1 for p in props if hud.get(p.bedrooms or 2))
    any_n = sum(
        1 for p in props if p.projected_monthly_rent or hud.get(p.bedrooms or 2)
    )

    print(f"# Rent coverage: {city}, {state} (county FIPS {fips})\n")
    print(f"Properties measured: {n} (VrmProperty rows for the market)\n")
    print("| Source | Properties with a rent | Notes |\n|---|---|---|")
    print(
        f"| VRM projected rent | {pct(vrm_n, n)} | stored on the row at scrape time |"
    )
    print(
        f"| HUD FMR (county, by bedrooms) | {pct(hud_n, n)} | rent floor (40th percentile), not market rent |"
    )
    if key:
        print(f"| Rentcast | {pct(rc_hits, rc_tried)} | sample of {rc_tried} |")
    else:
        print("| Rentcast | not measured | RENTCAST_API_KEY not set |")
    print("| Rentometer | not measured | no adapter in the codebase |")
    print(f"| Any source (VRM or HUD) | {pct(any_n, n)} | NFR-1 target: 90% |\n")

    if pairs:
        diffs = [(r - h) / r * 100 for h, r in pairs]
        print("## HUD FMR vs Rentcast\n")
        print(
            f"Paired samples: {len(pairs)}. HUD below Rentcast by median {median(diffs):.1f}%, "
            f"range {min(diffs):.1f}% to {max(diffs):.1f}%."
        )
    else:
        print(
            "## HUD FMR vs Rentcast\n\nNo paired samples: set RENTCAST_API_KEY and re-run."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
