from decimal import Decimal
from typing import List, Dict

from core.models import Listing


def get_comps_for_listing(listing: Listing) -> List[Dict]:
    """Return dummy comparable sales for a listing.

    Each comp: {address, price: Decimal, sq_ft: int, ppsf: Decimal}
    """
    base_ppsf = Decimal(listing.price) / Decimal(listing.sq_ft or 1)
    comps = []
    for i, factor in enumerate([Decimal("0.9"), Decimal("1.0"), Decimal("1.1")], start=1):
        ppsf = (base_ppsf * factor).quantize(Decimal("0.01"))
        price = (ppsf * Decimal(listing.sq_ft or 1)).quantize(Decimal("0.01"))
        comps.append({
            "address": f"Comp {i} - {listing.city}",
            "price": price,
            "sq_ft": listing.sq_ft or 0,
            "ppsf": ppsf,
        })
    return comps
