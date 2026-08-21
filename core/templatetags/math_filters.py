"""Math template filters for percentage calculations.

Provides:
  - mul: multiply a value by a factor (float/int/Decimal)
    Usage: {{ value|mul:100|floatformat:2 }}
  - sum_attr: sum a list of objects by attribute
    Usage: {{ queryset|sum_attr:"annual_reserve"|floatformat:2 }}
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def mul(value, arg):
    """Multiply the value by the argument."""
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except ValueError, TypeError, InvalidOperation:
        return value


@register.filter
def get_item(dictionary, key):
    """Look up a dictionary value by key. Usage: {{ dict|get_item:key }}."""
    try:
        return dictionary.get(key)
    except AttributeError, TypeError:
        return None


@register.filter
def sum_attr(queryset, attr_name):
    """Sum a queryset or list of objects by the given attribute name.

    Usage: {{ property.capex_items.all|sum_attr:"annual_reserve" }}
    """
    try:
        total = Decimal("0")
        for obj in queryset:
            val = getattr(obj, attr_name, None)
            if val is not None:
                total += Decimal(str(val))
        return total
    except ValueError, TypeError, InvalidOperation, AttributeError:
        return Decimal("0")
