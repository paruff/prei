from decimal import Decimal

import pytest

from investor_app.finance.utils import noi, cap_rate, cash_on_cash, dscr, irr


def test_noi_basic():
    assert noi(Decimal("1000"), Decimal("300")) == Decimal("8400")


def test_cap_rate_zero_price():
    assert cap_rate(Decimal("12000"), Decimal("0")) == Decimal("0")


def test_cash_on_cash_zero_invested():
    assert cash_on_cash(Decimal("12000"), Decimal("0")) == Decimal("0")


def test_dscr_zero_debt():
    assert dscr(Decimal("12000"), Decimal("0")) == Decimal("0")


def test_irr_simple_positive():
    cf = [Decimal("-100000")] + [Decimal("10000")] * 12
    result = irr(cf)
    assert isinstance(result, Decimal)
