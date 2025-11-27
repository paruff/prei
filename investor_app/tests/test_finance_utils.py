from decimal import Decimal

import pytest

from investor_app.finance import utils


def test_calculate_noi_simple():
    noi = utils.calculate_noi(Decimal("12000.00"), Decimal("3000.00"))
    assert isinstance(noi, Decimal)
    assert str(noi) == "9000.00"


def test_cap_rate_and_cash_on_cash():
    noi = Decimal("9000.00")
    price = Decimal("150000.00")
    cap = utils.calculate_cap_rate(noi, price)
    assert cap == Decimal("0.0600")  # 6.0%

    coc = utils.calculate_cash_on_cash(Decimal("3000.00"), Decimal("20000.00"))
    assert coc == Decimal("0.1500")  # 15.0%


def test_irr_basic():
    # initial investment = -1000, returns 500, 600
    irr = utils.calculate_irr([-1000, 500, 600])
    # IRR should be positive and roughly in the expected range
    assert isinstance(irr, Decimal)
    assert irr > Decimal("-1")  # sanity: not nan or invalid


def test_irr_invalid_raises():
    # Cashflows that cannot produce a meaningful IRR may raise
    with pytest.raises(ValueError):
        utils.calculate_irr([0, 0, 0])
