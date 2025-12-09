from decimal import Decimal
from core.models import Listing


def get_rent_estimate_for_listing(listing: Listing) -> Decimal:
    """Return a dummy monthly rent estimate using PPSF * 0.9 as heuristic."""
    if not listing.sq_ft:
        return Decimal("0")
    ppsf = Decimal(listing.price) / Decimal(listing.sq_ft)
    monthly = (ppsf * Decimal("0.9")).quantize(Decimal("0.01"))
    return monthly
