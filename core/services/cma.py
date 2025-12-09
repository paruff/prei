from decimal import Decimal
from typing import Iterable, Tuple

from core.models import Listing


def price_per_sqft(listing: Listing) -> Decimal:
    if not listing.sq_ft:
        return Decimal("0")
    return Decimal(listing.price) / Decimal(listing.sq_ft)


def find_undervalued(
    listings: Iterable[Listing], threshold: Decimal = Decimal("0.85")
) -> Iterable[Tuple[Listing, Decimal]]:
    """Return listings where PPSF is below the median * threshold.

    This is a simple CMA placeholder; later integrate comps API.
    """
    ppsf_values = [price_per_sqft(listing) for listing in listings if listing.sq_ft]
    if not ppsf_values:
        return []
    # median approximation
    sorted_vals = sorted(ppsf_values)
    mid = len(sorted_vals) // 2
    median = (
        sorted_vals[mid]
        if len(sorted_vals) % 2 == 1
        else (sorted_vals[mid - 1] + sorted_vals[mid]) / Decimal(2)
    )
    cutoff = median * threshold
    results = []
    for listing in listings:
        ppsf = price_per_sqft(listing)
        if ppsf and ppsf < cutoff:
            results.append((listing, ppsf))
    return results
