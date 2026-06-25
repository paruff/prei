"""Service layer for analytics (CMA, portfolio, property)."""

from core.services.portfolio import compute_portfolio_summary
from core.services.property_service import (
    calculate_noi,
    compute_noi,
    compute_noi_for_user,
    compute_noi_from_amounts,
)

__all__ = [
    "calculate_noi",
    "compute_noi",
    "compute_noi_for_user",
    "compute_noi_from_amounts",
    "compute_portfolio_summary",
]
