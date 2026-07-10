"""Tests for core validators (core/validators.py)."""

from __future__ import annotations

import pytest

from core.validators import (
    validate_foreclosure_stages,
    validate_location_parameter,
    validate_positive_decimal,
    validate_positive_integer,
    validate_property_types,
    validate_state_code,
)


class TestValidateStateCode:
    def test_valid_normalized(self) -> None:
        assert validate_state_code("tx") == "TX"
        assert validate_state_code(" CA ") == "CA"

    def test_invalid_raises(self) -> None:
        with pytest.raises(Exception):
            validate_state_code("XYZ")


class TestValidateLocationParameter:
    def test_valid_state_code(self) -> None:
        assert validate_location_parameter("TX") == "TX"

    def test_valid_city_name(self) -> None:
        assert validate_location_parameter("Austin") == "Austin"

    def test_empty_raises(self) -> None:
        with pytest.raises(Exception):
            validate_location_parameter("")


class TestValidateForeclosureStages:
    def test_comma_separated_string(self) -> None:
        result = validate_foreclosure_stages("preforeclosure,reo")
        assert "preforeclosure" in result

    def test_none_returns_empty(self) -> None:
        assert validate_foreclosure_stages(None) == []


class TestValidatePropertyTypes:
    def test_single_family_valid(self) -> None:
        result = validate_property_types("single-family,condo")
        assert "single-family" in result

    def test_none_returns_empty(self) -> None:
        assert validate_property_types(None) == []


class TestValidatePositiveInteger:
    def test_valid_string(self) -> None:
        assert validate_positive_integer("5", "f") == 5

    def test_none_returns_none(self) -> None:
        assert validate_positive_integer(None, "f") is None


class TestValidatePositiveDecimal:
    def test_valid_string(self) -> None:
        assert validate_positive_decimal("10.50", "f") == 10.50

    def test_none_returns_none(self) -> None:
        assert validate_positive_decimal(None, "f") is None
