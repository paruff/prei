"""Sensitivity analysis table for rent, vacancy, and rate scenarios.

Generates a table of underwriting metrics across varying parameter
combinations so analysts can see how NOI, Cap Rate, CoC, and MAO
respond to changes in key assumptions.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from decimal import Decimal
from typing import List, Dict, Any

from core.services.underwriting import UnderwritingInput, solve_underwriting


# ── Default scenario grids ────────────────────────────────────────────────────

# Rent multipliers relative to the base estimated_rent
DEFAULT_RENT_MULTIPLIERS: list[Decimal] = [
    Decimal("0.80"),
    Decimal("0.90"),
    Decimal("1.00"),
    Decimal("1.10"),
    Decimal("1.20"),
]

# Vacancy rates to test
DEFAULT_VACANCY_RATES: list[Decimal] = [
    Decimal("0.03"),
    Decimal("0.05"),
    Decimal("0.07"),
    Decimal("0.10"),
    Decimal("0.15"),
]

# Cap rates to backsolve MAO against
DEFAULT_CAP_RATES: list[Decimal | float] = [0.05, 0.06, 0.07, 0.08, 0.09, 0.10]


# ── Public API ─────────────────────────────────────────────────────────────────


def sensitivity_analysis_table(
    base_inputs: UnderwritingInput,
    rent_multipliers: Sequence[Decimal] | None = None,
    vacancy_rates: Sequence[Decimal] | None = None,
    cap_rate_scanners: Sequence[Decimal | float] | None = None,
) -> List[Dict[str, Any]]:
    """Generate a sensitivity analysis table across rent, vacancy, and rate scenarios.

    The "rate scenario" dimension varies the cap rate used to backsolve the
    Max Allowable Offer (MAO = NOI / cap_rate). Each row therefore shows the
    offer an investor would make at that required return.

    Args:
        base_inputs: Base UnderwritingInput with property financial data.
        rent_multipliers: Rent multiplier list relative to base estimated_rent.
            Defaults to [80%, 90%, 100%, 110%, 120%].
        vacancy_rates: List of vacancy rates to test. Defaults to
            [3%, 5%, 7%, 10%, 15%].
        cap_rate_scanners: List of cap rates to backsolve MAO for.
            Defaults to [5%, 6%, 7%, 8%, 9%, 10%].

    Returns:
        A list of dicts, each dict representing one table row with keys:
        - "rent": the gross annual rent used (Decimal)
        - "vacancy_rate": the vacancy rate used (Decimal)
        - "cap_rate": the cap rate tested (Decimal | float)
        - "noi": Net Operating Income (Decimal)
        - "cap_rate_result": computed cap rate from NOI/price (Decimal)
        - "cash_on_cash": Cash-on-Cash yield (Decimal)
        - "mao": Max Allowable Offer at the given cap rate (Decimal)
    """
    rents = rent_multipliers or DEFAULT_RENT_MULTIPLIERS
    vacancies = vacancy_rates or DEFAULT_VACANCY_RATES
    caps = cap_rate_scanners or DEFAULT_CAP_RATES

    rows: List[Dict[str, Any]] = []

    for mult in rents:
        rent = base_inputs.estimated_rent * mult
        inputs_rent = replace(base_inputs, estimated_rent=rent)

        for vac in vacancies:
            inputs_vac = replace(inputs_rent, vacancy_rate=vac)

            for cap in caps:
                metrics = solve_underwriting(inputs_vac, cap)

                rows.append(
                    {
                        "rent": rent,
                        "vacancy_rate": vac,
                        "cap_rate": cap,
                        "noi": metrics.noi,
                        "cap_rate_result": metrics.cap_rate,
                        "cash_on_cash": metrics.cash_on_cash,
                        "mao": metrics.mao,
                    }
                )

    return rows
