from __future__ import annotations

import pytest
from rest_framework import serializers

from core.validators import (
    VALID_US_STATES,
    validate_foreclosure_stages,
    validate_location_parameter,
    validate_min_growth_score,
    validate_positive_decimal,
    validate_positive_integer,
    validate_property_types,
    validate_state_code,
)


class TestValidateStateCode:
    """Tests for state code validation."""

    def test_validate_state_code_accepts_valid_codes(self):
        """Test that all valid US state codes are accepted."""
        for state in ["CA", "TX", "NY", "FL", "WA"]:
            assert validate_state_code(state) == state

    def test_validate_state_code_rejects_invalid_codes(self):
        """Test that invalid state codes are rejected."""
        with pytest.raises(serializers.ValidationError):
            validate_state_code("ZZ")

        with pytest.raises(serializers.ValidationError):
            validate_state_code("ABC")

    def test_validate_state_code_normalizes_lowercase(self):
        """Test that lowercase state codes are normalized to uppercase."""
        assert validate_state_code("ca") == "CA"
        assert validate_state_code("tx") == "TX"

    def test_validate_state_code_strips_whitespace(self):
        """Test that whitespace is stripped from state codes."""
        assert validate_state_code(" CA ") == "CA"
        assert validate_state_code("TX\n") == "TX"

    def test_validate_state_code_rejects_empty_string(self):
        """Test that empty string is rejected."""
        with pytest.raises(serializers.ValidationError):
            validate_state_code("")

    def test_validate_state_code_rejects_wrong_length(self):
        """Test that codes with wrong length are rejected."""
        with pytest.raises(serializers.ValidationError):
            validate_state_code("C")

        with pytest.raises(serializers.ValidationError):
            validate_state_code("CAL")


class TestValidateMinGrowthScore:
    """Tests for minimum growth score validation."""

    def test_validate_min_growth_score_accepts_valid_values(self):
        """Test that valid scores are accepted."""
        assert validate_min_growth_score("50") == 50.0
        assert validate_min_growth_score(75) == 75.0
        assert validate_min_growth_score(0) == 0.0
        assert validate_min_growth_score(100) == 100.0

    def test_validate_min_growth_score_rejects_negative(self):
        """Test that negative scores are rejected."""
        with pytest.raises(serializers.ValidationError):
            validate_min_growth_score(-1)

    def test_validate_min_growth_score_rejects_above_100(self):
        """Test that scores above 100 are rejected."""
        with pytest.raises(serializers.ValidationError):
            validate_min_growth_score(101)

    def test_validate_min_growth_score_defaults_to_50(self):
        """Test that None defaults to 50."""
        assert validate_min_growth_score(None) == 50.0

    def test_validate_min_growth_score_rejects_non_numeric(self):
        """Test that non-numeric values are rejected."""
        with pytest.raises(serializers.ValidationError):
            validate_min_growth_score("invalid")


class TestValidUSStates:
    """Test that VALID_US_STATES contains expected values."""

    def test_valid_us_states_contains_all_50_states(self):
        """Test that all 50 states are in the set."""
        states_50 = {
            "AL",
            "AK",
            "AZ",
            "AR",
            "CA",
            "CO",
            "CT",
            "DE",
            "FL",
            "GA",
            "HI",
            "ID",
            "IL",
            "IN",
            "IA",
            "KS",
            "KY",
            "LA",
            "ME",
            "MD",
            "MA",
            "MI",
            "MN",
            "MS",
            "MO",
            "MT",
            "NE",
            "NV",
            "NH",
            "NJ",
            "NM",
            "NY",
            "NC",
            "ND",
            "OH",
            "OK",
            "OR",
            "PA",
            "RI",
            "SC",
            "SD",
            "TN",
            "TX",
            "UT",
            "VT",
            "VA",
            "WA",
            "WV",
            "WI",
            "WY",
        }
        for state in states_50:
            assert state in VALID_US_STATES

    def test_valid_us_states_contains_territories(self):
        """Test that territories are included."""
        territories = {"DC", "PR", "VI", "GU", "AS", "MP"}
        for territory in territories:
            assert territory in VALID_US_STATES


class TestValidateLocationParameter:
    """Tests for location parameter validation."""

    def test_accepts_valid_city_state(self):
        """Test that valid city, state format is accepted."""
        assert validate_location_parameter("Miami, FL") == "Miami, FL"
        assert validate_location_parameter("Austin, TX") == "Austin, TX"

    def test_accepts_valid_zip_code(self):
        """Test that valid ZIP codes are accepted."""
        assert validate_location_parameter("33139") == "33139"
        assert validate_location_parameter("78701") == "78701"

    def test_accepts_valid_state_code(self):
        """Test that valid state codes are accepted."""
        assert validate_location_parameter("FL") == "FL"
        assert validate_location_parameter("TX") == "TX"

    def test_accepts_county_name(self):
        """Test that county names are accepted."""
        assert validate_location_parameter("Miami-Dade County") == "Miami-Dade County"

    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        assert validate_location_parameter(" Miami, FL ") == "Miami, FL"

    def test_rejects_empty_string(self):
        """Test that empty string is rejected."""
        with pytest.raises(serializers.ValidationError):
            validate_location_parameter("")

    def test_rejects_none(self):
        """Test that None is rejected."""
        with pytest.raises(serializers.ValidationError):
            validate_location_parameter(None)


class TestValidateForeclosureStages:
    """Tests for foreclosure stage validation."""

    def test_accepts_single_valid_stage(self):
        """Test that single valid stage is accepted."""
        assert validate_foreclosure_stages("auction") == ["auction"]
        assert validate_foreclosure_stages("preforeclosure") == ["preforeclosure"]

    def test_accepts_multiple_valid_stages(self):
        """Test that multiple valid stages are accepted."""
        result = validate_foreclosure_stages("auction,preforeclosure,reo")
        assert set(result) == {"auction", "preforeclosure", "reo"}

    def test_normalizes_case(self):
        """Test that stage names are normalized to lowercase."""
        assert validate_foreclosure_stages("AUCTION") == ["auction"]
        assert validate_foreclosure_stages("Auction,REO") == ["auction", "reo"]

    def test_strips_whitespace(self):
        """Test that whitespace is stripped from stage names."""
        result = validate_foreclosure_stages(" auction , reo ")
        assert set(result) == {"auction", "reo"}

    def test_rejects_invalid_stage(self):
        """Test that invalid stages are rejected."""
        with pytest.raises(serializers.ValidationError):
            validate_foreclosure_stages("invalid_stage")

    def test_returns_empty_list_for_none(self):
        """Test that None returns empty list."""
        assert validate_foreclosure_stages(None) == []


class TestValidatePropertyTypes:
    """Tests for property type validation."""

    def test_accepts_single_valid_type(self):
        """Test that single valid type is accepted."""
        assert validate_property_types("single-family") == ["single-family"]
        assert validate_property_types("condo") == ["condo"]

    def test_accepts_multiple_valid_types(self):
        """Test that multiple valid types are accepted."""
        result = validate_property_types("single-family,condo,multi-family")
        assert set(result) == {"single-family", "condo", "multi-family"}

    def test_normalizes_case(self):
        """Test that type names are normalized to lowercase."""
        assert validate_property_types("SINGLE-FAMILY") == ["single-family"]

    def test_rejects_invalid_type(self):
        """Test that invalid types are rejected."""
        with pytest.raises(serializers.ValidationError):
            validate_property_types("invalid_type")

    def test_returns_empty_list_for_none(self):
        """Test that None returns empty list."""
        assert validate_property_types(None) == []


class TestValidatePositiveInteger:
    """Tests for positive integer validation."""

    def test_accepts_valid_positive_integer(self):
        """Test that valid positive integers are accepted."""
        assert validate_positive_integer("5", "testField") == 5
        assert validate_positive_integer("100", "testField") == 100

    def test_accepts_zero(self):
        """Test that zero is accepted."""
        assert validate_positive_integer("0", "testField") == 0

    def test_rejects_negative_integer(self):
        """Test that negative integers are rejected."""
        with pytest.raises(serializers.ValidationError):
            validate_positive_integer("-5", "testField")

    def test_rejects_non_numeric(self):
        """Test that non-numeric values are rejected."""
        with pytest.raises(serializers.ValidationError):
            validate_positive_integer("invalid", "testField")

    def test_returns_none_for_none(self):
        """Test that None returns None."""
        assert validate_positive_integer(None, "testField") is None

    def test_returns_none_for_empty_string(self):
        """Test that empty string returns None."""
        assert validate_positive_integer("", "testField") is None


class TestValidatePositiveDecimal:
    """Tests for positive decimal validation."""

    def test_accepts_valid_positive_decimal(self):
        """Test that valid positive decimals are accepted."""
        assert validate_positive_decimal("5.5", "testField") == 5.5
        assert validate_positive_decimal("100.25", "testField") == 100.25

    def test_accepts_zero(self):
        """Test that zero is accepted."""
        assert validate_positive_decimal("0", "testField") == 0.0

    def test_rejects_negative_decimal(self):
        """Test that negative decimals are rejected."""
        with pytest.raises(serializers.ValidationError):
            validate_positive_decimal("-5.5", "testField")

    def test_rejects_non_numeric(self):
        """Test that non-numeric values are rejected."""
        with pytest.raises(serializers.ValidationError):
            validate_positive_decimal("invalid", "testField")

    def test_returns_none_for_none(self):
        """Test that None returns None."""
        assert validate_positive_decimal(None, "testField") is None

    def test_returns_none_for_empty_string(self):
        """Test that empty string returns None."""
        assert validate_positive_decimal("", "testField") is None
