from __future__ import annotations

import pytest
from decimal import Decimal
from rest_framework import serializers

from core.validators import validate_state_code, validate_min_growth_score, VALID_US_STATES


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
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
        }
        for state in states_50:
            assert state in VALID_US_STATES

    def test_valid_us_states_contains_territories(self):
        """Test that territories are included."""
        territories = {"DC", "PR", "VI", "GU", "AS", "MP"}
        for territory in territories:
            assert territory in VALID_US_STATES
