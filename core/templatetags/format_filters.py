"""One format for money, percentages and scores in every template (FR-15).

  {{ 95000|money }}        -> $95,000       {{ x|money:2 }} -> $95,000.50
  {{ 0.0744|pct }}         -> 7.44%         {{ 7.44|pct:"pts" }} -> 7.44%
  {{ 7.4|score }}          -> 7.40
Missing or non-numeric values render as an em dash.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import template

register = template.Library()

EMPTY = "—"


def _to_decimal(value) -> Decimal | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def _fixed(number: Decimal, places: int) -> str:
    quantum = Decimal(1).scaleb(-places)
    rounded = number.quantize(quantum, rounding=ROUND_HALF_UP)
    return f"{rounded:,.{places}f}"


@register.filter
def money(value, places=0):
    """Dollar amount with thousands separators; negatives as -$1,200."""
    number = _to_decimal(value)
    if number is None:
        return EMPTY
    text = _fixed(abs(number), int(places))
    sign = "-" if number < 0 and Decimal(text.replace(",", "")) != 0 else ""
    return f"{sign}${text}"


@register.filter
def pct(value, unit="fraction"):
    """Percentage with 2 decimals. Input is a fraction (0.0744) unless unit is "pts"."""
    number = _to_decimal(value)
    if number is None:
        return EMPTY
    if unit == "fraction":
        number *= 100
    elif unit != "pts":
        raise ValueError(f"pct unit must be 'fraction' or 'pts', got {unit!r}")
    return f"{_fixed(number, 2)}%"


@register.filter
def score(value):
    """Score (GACS, investment score) with 2 decimals."""
    number = _to_decimal(value)
    return EMPTY if number is None else _fixed(number, 2)
