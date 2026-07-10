"""Math template filters for percentage calculations.

Provides:
  - mul: multiply a value by a factor (float/int/Decimal)
    Usage: {{ value|mul:100|floatformat:2 }}
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
