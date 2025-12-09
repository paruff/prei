from decimal import Decimal
from typing import Dict

from core.models import Property
from investor_app.finance.utils import (
    compute_analysis_for_property,
    to_decimal,
)


def aggregate_portfolio(user) -> Dict[str, Decimal]:
    """Aggregate KPIs across a user's properties.

    Returns totals/averages for NOI, cap rate, cash-on-cash.
    """
    props = Property.objects.filter(user=user)
    total_noi = Decimal("0")
    cap_rates = []
    cocs = []
    for p in props:
        analysis = compute_analysis_for_property(p)
        total_noi += to_decimal(analysis.noi)
        cap_rates.append(to_decimal(analysis.cap_rate))
        cocs.append(to_decimal(analysis.cash_on_cash))

    avg_cap_rate = sum(cap_rates, Decimal("0")) / Decimal(len(cap_rates)) if cap_rates else Decimal("0")
    avg_coc = sum(cocs, Decimal("0")) / Decimal(len(cocs)) if cocs else Decimal("0")
    return {
        "total_noi": total_noi,
        "avg_cap_rate": avg_cap_rate,
        "avg_coc": avg_coc,
    }
