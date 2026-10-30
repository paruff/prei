from decimal import Decimal
from types import SimpleNamespace

import pytest

from core.services.pipeline import underwriting_summary

pytestmark = pytest.mark.unit


def _pp(price, rent):
    return SimpleNamespace(price=price, estimated_rent=rent)


def test_yield_and_price_to_rent():
    out = underwriting_summary(_pp(Decimal("180000"), Decimal("1800")))
    assert out is not None
    assert round(out["gross_yield_pct"], 1) == Decimal("12.0")
    assert round(out["price_to_rent"], 2) == Decimal("8.33")
    assert out["noi"] > 0 and out["dscr"] > 0


@pytest.mark.parametrize(
    "price,rent",
    [
        (None, Decimal("1")),
        (Decimal("1"), None),
        (Decimal("0"), Decimal("1")),
        (Decimal("1"), Decimal("0")),
    ],
)
def test_missing_inputs_return_none(price, rent):
    assert underwriting_summary(_pp(price, rent)) is None
