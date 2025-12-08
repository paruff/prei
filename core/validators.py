from __future__ import annotations

from rest_framework import serializers

# Valid US state and territory codes
VALID_US_STATES = {
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
    "DC",
    "PR",
    "VI",
    "GU",
    "AS",
    "MP",
}


def validate_state_code(state_code: str) -> str:
    """
    Validate and normalize a US state code.

    Args:
        state_code: The state code to validate (can be lowercase or have whitespace)

    Returns:
        The normalized uppercase state code

    Raises:
        serializers.ValidationError: If the state code is invalid
    """
    if not state_code:
        raise serializers.ValidationError(
            "Invalid state code. Please use 2-letter US state abbreviations."
        )

    # Normalize: strip whitespace and convert to uppercase
    normalized = state_code.strip().upper()

    # Validate length
    if len(normalized) != 2:
        raise serializers.ValidationError(
            "Invalid state code. Please use 2-letter US state abbreviations."
        )

    # Validate it's a valid US state/territory
    if normalized not in VALID_US_STATES:
        raise serializers.ValidationError(
            "Invalid state code. Please use 2-letter US state abbreviations."
        )

    return normalized


def validate_min_growth_score(score: str | int | float | None) -> float:
    """
    Validate minimum growth score parameter.

    Args:
        score: The minimum growth score to validate

    Returns:
        The validated score as a float

    Raises:
        serializers.ValidationError: If the score is invalid
    """
    if score is None:
        return 50.0  # Default value

    try:
        score_float = float(score)
    except (ValueError, TypeError):
        raise serializers.ValidationError(
            "minGrowthScore must be a number between 0 and 100."
        )

    if score_float < 0 or score_float > 100:
        raise serializers.ValidationError(
            "minGrowthScore must be between 0 and 100."
        )

    return score_float
