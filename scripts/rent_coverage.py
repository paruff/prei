"""Rent coverage by source on the seeded market (NFR-7, AC-13). Prints Markdown.

Run in the container (after `make docker-seed`):
    make docker-rent-report SEED_ARGS="--city Dallas --state TX"
or: python scripts/rent_coverage.py --city Dallas --state TX

Sources: VRM projected rent (stored), HUD FMR (ZIP-level Small Area FMR where HUD
publishes it, else metro/county level), Rentcast ZIP market statistics (only when
RENTCAST_API_KEY is set and its subscription is active). Rentometer has no adapter,
so it is not measured.
"""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal
from statistics import median

import django
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "investor_app.settings")
django.setup()

from django.conf import settings  # noqa: E402

from core.integrations.market.fmr_adapter import fetch_fmr_entity_id  # noqa: E402
from core.integrations.market.hud_fmr import FMRClient  # noqa: E402
from core.models import GrowthArea, VrmProperty  # noqa: E402

BED_KEY = {
    0: "Efficiency",
    1: "One-Bedroom",
    2: "Two-Bedroom",
    3: "Three-Bedroom",
    4: "Four-Bedroom",
}
FMR_YEAR = 2026
RENTCAST_MARKETS = "https://api.rentcast.io/v1/markets"


def pct(n: int, total: int) -> str:
    return f"{n}/{total} ({100 * n / total:.0f}%)" if total else "0/0"


def hud_rows(state: str, city: str) -> tuple[dict[str, dict], str | None]:
    """HUD FMR rows keyed by ZIP (plus 'MSA level'); error text if unavailable."""
    entity = fetch_fmr_entity_id(state, city)
    if not entity:
        return {}, "no HUD entity id for the market (token missing FMR access?)"
    try:
        data = FMRClient()._get(f"data/{entity}", params={"year": str(FMR_YEAR)})[
            "data"
        ]
    except Exception as exc:  # reported in the output, not swallowed
        return {}, f"HUD request failed: {exc}"
    basic = data.get("basicdata") or []
    if isinstance(basic, dict):  # non-Small-Area markets return one row
        return {"MSA level": basic}, None
    return {str(r.get("zip_code")): r for r in basic}, None


def rentcast_zip(zip_code: str, key: str) -> tuple[dict[int, Decimal], str | None]:
    """Rentcast median rent by bedroom count for a ZIP; error text on failure."""
    try:
        resp = requests.get(
            RENTCAST_MARKETS,
            params={"zipCode": zip_code, "dataType": "Rental"},
            headers={"X-Api-Key": key},
            timeout=15,
        )
        if not resp.ok:
            return {}, f"{resp.status_code} {resp.json().get('error', resp.text[:80])}"
        rows = resp.json().get("rentalData", {}).get("dataByBedrooms") or []
        out = {
            int(r["bedrooms"]): Decimal(str(r.get("medianRent") or r["averageRent"]))
            for r in rows
            if r.get("medianRent") or r.get("averageRent")
        }
        return out, None if out else "no per-bedroom rows in response"
    except Exception as exc:  # reported in the output, not swallowed
        return {}, f"Rentcast request failed: {exc}"


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

    hud, hud_err = hud_rows(state, city)

    def hud_rent(p: VrmProperty) -> tuple[Decimal | None, str]:
        beds = p.bedrooms if p.bedrooms in BED_KEY else 2
        for level in (p.zip_code, "MSA level"):
            row = hud.get(level)
            if row and row.get(BED_KEY[beds]):
                return Decimal(str(row[BED_KEY[beds]])), level
        return None, ""

    key = getattr(settings, "RENTCAST_API_KEY", "") or os.environ.get(
        "RENTCAST_API_KEY", ""
    )
    rc: dict[str, dict[int, Decimal]] = {}
    rc_errs: dict[str, str] = {}
    if key:
        for z in sorted({p.zip_code for p in props}):
            rc[z], err = rentcast_zip(z, key)
            if err:
                rc_errs[z] = err

    n = len(props)
    hud_hits = [hud_rent(p) for p in props]
    vrm_n = sum(1 for p in props if p.projected_monthly_rent)
    hud_n = sum(1 for h, _ in hud_hits if h)
    zip_n = sum(1 for h, lvl in hud_hits if h and lvl != "MSA level")
    any_n = sum(
        1 for p, (h, _) in zip(props, hud_hits) if p.projected_monthly_rent or h
    )
    rc_n = sum(1 for p in props if rc.get(p.zip_code, {}).get(p.bedrooms or 2))

    print(f"# Rent coverage: {city}, {state} (county FIPS {area.county_fips})\n")
    print(f"Properties measured: {n} (VrmProperty rows for the market)\n")
    print("| Source | Properties with a rent | Notes |\n|---|---|---|")
    print(
        f"| VRM projected rent | {pct(vrm_n, n)} | stored on the row at scrape time |"
    )
    hud_note = (
        hud_err
        or f"FY{FMR_YEAR}; {zip_n} at ZIP level (Small Area FMR), rest metro level; 40th percentile floor"
    )
    print(f"| HUD FMR | {pct(hud_n, n)} | {hud_note} |")
    if not key:
        print("| Rentcast | not measured | RENTCAST_API_KEY not set |")
    elif rc_errs:
        print(
            f"| Rentcast | not measured | {'; '.join(f'{z}: {e}' for z, e in rc_errs.items())} |"
        )
    else:
        print(
            f"| Rentcast (ZIP market stats) | {pct(rc_n, n)} | median rent by bedrooms |"
        )
    print("| Rentometer | not measured | no adapter in the codebase |")
    print(f"| Any source (VRM or HUD) | {pct(any_n, n)} | NFR-1 target: 90% |\n")

    print("## HUD FMR vs Rentcast\n")
    print(
        "| ZIP | Beds | HUD FMR | Level | Rentcast median | HUD below Rentcast |\n|---|---|---|---|---|---|"
    )
    diffs: list[Decimal] = []
    for p, (h, lvl) in zip(props, hud_hits):
        beds = p.bedrooms or 2
        r = rc.get(p.zip_code, {}).get(beds)
        gap = ""
        if h and r:
            d = (r - h) / r * 100
            diffs.append(d)
            gap = f"{d:.1f}%"
        print(
            f"| {p.zip_code} | {beds} | {h or 'n/a'} | {lvl or 'n/a'} | {r or 'n/a'} | {gap or 'n/a'} |"
        )
    if diffs:
        print(
            f"\nPaired ZIPs: {len(diffs)}. HUD below Rentcast by median {median(diffs):.1f}%, range {min(diffs):.1f}% to {max(diffs):.1f}%."
        )
    else:
        print("\nNo paired samples (see the Rentcast row above).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
