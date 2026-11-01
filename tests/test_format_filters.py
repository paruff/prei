from decimal import Decimal

import pytest

from core.templatetags.format_filters import money, pct, score


@pytest.mark.parametrize(
    "value,places,expected",
    [
        (95000, 0, "$95,000"),
        ("95000.00", 0, "$95,000"),
        (Decimal("450000.5"), 0, "$450,001"),
        (Decimal("1234.5"), 2, "$1,234.50"),
        (-1200, 0, "-$1,200"),
        (Decimal("-0.4"), 0, "$0"),
        (0, 0, "$0"),
        (None, 0, "—"),
        ("", 0, "—"),
        ("n/a", 0, "—"),
    ],
)
def test_money(value, places, expected):
    assert money(value, places) == expected


@pytest.mark.parametrize(
    "value,unit,expected",
    [
        (Decimal("0.0744"), "fraction", "7.44%"),
        (0.01, "fraction", "1.00%"),
        (Decimal("7.44"), "pts", "7.44%"),
        ("-0.0001", "fraction", "-0.01%"),
        (None, "fraction", "—"),
        ("x", "pts", "—"),
    ],
)
def test_pct(value, unit, expected):
    assert pct(value, unit) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (7.44, "7.44"),
        (Decimal("7.4400"), "7.44"),
        (7.4, "7.40"),
        (None, "—"),
        (float("nan"), "—"),
    ],
)
def test_score(value, expected):
    assert score(value) == expected


def test_no_template_formats_money_or_percent_by_hand():
    import re
    from pathlib import Path

    pattern = re.compile(r"\$\{\{|\}\}\s*%")
    offenders = [
        f"{path}:{n}"
        for path in (Path(__file__).resolve().parent.parent / "templates").rglob(
            "*.html"
        )
        for n, line in enumerate(path.read_text().splitlines(), 1)
        if pattern.search(line)
    ]
    assert not offenders, offenders


def test_pct_rejects_unknown_unit():
    with pytest.raises(ValueError):
        pct(0.1, "pt")
