# core.templatetags

## Overview
Django template filter libraries for display formatting and simple arithmetic. Each module exposes `register = template.Library()`.

## Interface
- `format_filters.py` (`{% load format_filters %}`): `money(value, places=0)`, `pct(value, unit="fraction")`, `score(value)`, `enum_label(value)`; constant `EMPTY = "—"`; private helpers `_to_decimal`, `_fixed`.
- `math_filters.py` (`{% load math_filters %}`): `mul`, `sub`, `get_item`, `sum_attr`.

## Invariants
- `money`, `pct`, `score` and `enum_label` return `EMPTY` for missing values (None, and "" for `enum_label`) instead of raising.
- `pct` treats input as a fraction (0.0744 -> 7.44%) unless `unit="pts"`; any other unit raises `ValueError`.
- `money` renders negatives as `-$1,200` and never renders `-$0`.
- Filters are pure and do not touch the database or network.

## Side Effects
- None.

## Verification
- Run: `.venv/bin/python -m pytest tests/` (pytest.ini; pass specific paths for speed)
