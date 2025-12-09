from decimal import Decimal


def get_crime_score(zip_code: str | None = None, city: str | None = None, state: str | None = None) -> Decimal:
    """Return a dummy crime score (lower is better)."""
    base = Decimal("3.0")
    if state == "TX":
        base = Decimal("2.5")
    if state == "CA":
        base = Decimal("3.5")
    return base
