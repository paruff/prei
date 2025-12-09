from decimal import Decimal


def get_school_rating(zip_code: str | None = None, city: str | None = None, state: str | None = None) -> Decimal:
    """Return a dummy school rating (0-10)."""
    if state == "TX":
        return Decimal("8.0")
    if state == "CA":
        return Decimal("7.0")
    return Decimal("6.5")
