from decimal import Decimal
from typing import Dict, List

from django.conf import settings

from core.models import Property
from investor_app.finance.utils import (
    cap_rate,
    cash_on_cash,
    compute_analysis_for_property,
    noi,
    to_decimal,
)


def aggregate_portfolio(user) -> Dict[str, Decimal]:
    """Aggregate KPIs across a user's properties.

    Returns totals/averages for NOI, cap rate, cash-on-cash.
    """
    props = Property.objects.filter(user=user)
    total_noi = Decimal("0")
    cap_rates: List[Decimal] = []
    cocs: List[Decimal] = []
    for p in props:
        analysis = compute_analysis_for_property(p)
        total_noi += to_decimal(analysis.noi)
        cap_rates.append(to_decimal(analysis.cap_rate))
        cocs.append(to_decimal(analysis.cash_on_cash))

    avg_cap_rate = (
        sum(cap_rates, Decimal("0")) / Decimal(len(cap_rates))
        if cap_rates
        else Decimal("0")
    )
    avg_coc = sum(cocs, Decimal("0")) / Decimal(len(cocs)) if cocs else Decimal("0")
    return {
        "total_noi": total_noi,
        "avg_cap_rate": avg_cap_rate,
        "avg_coc": avg_coc,
    }


def _compute_property_kpis_with_overrides(
    prop: Property, overrides: Dict
) -> Dict[str, Decimal]:
    """Compute KPIs for a single property applying scenario overrides.

    Does NOT persist anything to the database — purely ephemeral.

    Args:
        prop: The property to compute KPIs for.
        overrides: Dict with optional keys:
            - ``vacancy_rate`` (Decimal 0–1, e.g. ``Decimal("0.10")`` for 10 %)
            - ``purchase_price_delta_pct`` (Decimal %, e.g. ``Decimal("-10")`` for −10 %)
            - ``interest_rate`` (Decimal %, reserved for future debt-service calculation)

    Returns:
        Dict with keys ``noi``, ``cap_rate``, ``coc`` (all ``Decimal``).
    """
    defaults = settings.FINANCE_DEFAULTS

    if "vacancy_rate" in overrides:
        vacancy_rate = Decimal(str(overrides["vacancy_rate"]))
    else:
        vacancy_rate = Decimal(str(defaults["vacancy_rate"]))

    purchase_price_delta_pct = Decimal(
        str(overrides.get("purchase_price_delta_pct", "0"))
    )

    base_price = to_decimal(prop.purchase_price)
    purchase_price = base_price * (
        Decimal("1") + purchase_price_delta_pct / Decimal("100")
    )

    if purchase_price <= Decimal("0"):
        return {
            "noi": Decimal("0"),
            "cap_rate": Decimal("0"),
            "coc": Decimal("0"),
        }

    incomes = prop.rental_incomes.all()
    expenses = prop.operating_expenses.all()

    monthly_income = sum(
        (to_decimal(ri.monthly_rent) * (Decimal("1") - vacancy_rate) for ri in incomes),
        Decimal("0"),
    )
    monthly_expense = sum((oe.monthly_amount() for oe in expenses), Decimal("0"))
    annual_noi = noi(monthly_income, monthly_expense)

    cap_rate_val = cap_rate(annual_noi, purchase_price)
    coc_val = cash_on_cash(annual_noi, purchase_price)

    return {
        "noi": annual_noi,
        "cap_rate": cap_rate_val,
        "coc": coc_val,
    }


def run_scenario(user, overrides: Dict) -> Dict[str, Decimal]:
    """Apply scenario overrides to all user properties and return aggregate KPIs.

    Scenarios are ephemeral — no data is written to the database.

    Args:
        user: Django ``User`` instance.
        overrides: Dict with optional keys ``vacancy_rate``,
            ``purchase_price_delta_pct``, and ``interest_rate``.

    Returns:
        Dict with keys ``total_noi``, ``avg_cap_rate``, ``avg_coc`` (all ``Decimal``).
        Returns zeroed dict when the user has no properties.
    """
    props = Property.objects.filter(user=user)
    total_noi = Decimal("0")
    cap_rates: List[Decimal] = []
    cocs: List[Decimal] = []

    for p in props:
        kpis = _compute_property_kpis_with_overrides(p, overrides)
        total_noi += kpis["noi"]
        cap_rates.append(kpis["cap_rate"])
        cocs.append(kpis["coc"])

    avg_cap_rate = (
        sum(cap_rates, Decimal("0")) / Decimal(len(cap_rates))
        if cap_rates
        else Decimal("0")
    )
    avg_coc = sum(cocs, Decimal("0")) / Decimal(len(cocs)) if cocs else Decimal("0")

    return {
        "total_noi": total_noi,
        "avg_cap_rate": avg_cap_rate,
        "avg_coc": avg_coc,
    }


def compare_scenarios(user, scenarios: List[Dict]) -> List[Dict]:
    """Compare multiple scenario overrides across a user's portfolio.

    Args:
        user: Django ``User`` instance.
        scenarios: List of override dicts. Each may include a ``label`` key;
            missing labels default to ``"Scenario N"`` (1-indexed).

    Returns:
        List of dicts with keys ``label``, ``total_noi``, ``avg_cap_rate``,
        ``avg_coc``.
    """
    results = []
    for i, scenario in enumerate(scenarios):
        label = scenario.get("label", f"Scenario {i + 1}")
        kpis = run_scenario(user, scenario)
        results.append({"label": label, **kpis})
    return results
