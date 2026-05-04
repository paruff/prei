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
        raise serializers.ValidationError("minGrowthScore must be between 0 and 100.")

    return score_float


def validate_location_parameter(location: str) -> str:
    """
    Validate geographic location parameter.

    Args:
        location: Geographic identifier (city/state, county, ZIP, or state code)

    Returns:
        The validated and normalized location string

    Raises:
        serializers.ValidationError: If location is invalid or missing
    """
    if not location:
        raise serializers.ValidationError(
            "Invalid geographic area. Please provide a valid city, county, ZIP code, or state."
        )

    # Normalize: strip whitespace
    normalized = location.strip()

    if not normalized:
        raise serializers.ValidationError(
            "Invalid geographic area. Please provide a valid city, county, ZIP code, or state."
        )

    return normalized


def validate_foreclosure_stages(stages: str | None) -> list[str]:
    """
    Validate and parse foreclosure stage filter.

    Args:
        stages: Comma-separated foreclosure stages

    Returns:
        List of validated stage codes

    Raises:
        serializers.ValidationError: If any stage is invalid
    """
    valid_stages = {"preforeclosure", "auction", "reo", "government"}

    if not stages:
        return []

    stage_list = [s.strip().lower() for s in stages.split(",")]

    for stage in stage_list:
        if stage not in valid_stages:
            raise serializers.ValidationError(
                f"Invalid foreclosure stage '{stage}'. Valid options: preforeclosure, auction, reo, government"
            )

    return stage_list


def validate_property_types(types: str | None) -> list[str]:
    """
    Validate and parse property type filter.

    Args:
        types: Comma-separated property types

    Returns:
        List of validated property type codes

    Raises:
        serializers.ValidationError: If any type is invalid
    """
    valid_types = {"single-family", "condo", "multi-family", "commercial"}

    if not types:
        return []

    type_list = [t.strip().lower() for t in types.split(",")]

    for ptype in type_list:
        if ptype not in valid_types:
            raise serializers.ValidationError(
                f"Invalid property type '{ptype}'. Valid options: single-family, condo, multi-family, commercial"
            )

    return type_list


def validate_positive_integer(value: str | int | None, field_name: str) -> int | None:
    """
    Validate a positive integer parameter.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages

    Returns:
        Validated integer or None

    Raises:
        serializers.ValidationError: If value is invalid
    """
    if value is None or value == "":
        return None

    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise serializers.ValidationError(f"{field_name} must be a positive integer.")

    if int_value < 0:
        raise serializers.ValidationError(f"{field_name} must be a positive integer.")

    return int_value


def validate_positive_decimal(
    value: str | float | None, field_name: str
) -> float | None:
    """
    Validate a positive decimal parameter.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages

    Returns:
        Validated float or None

    Raises:
        serializers.ValidationError: If value is invalid
    """
    if value is None or value == "":
        return None

    try:
        float_value = float(value)
    except (ValueError, TypeError):
        raise serializers.ValidationError(f"{field_name} must be a positive number.")

    if float_value < 0:
        raise serializers.ValidationError(f"{field_name} must be a positive number.")

    return float_value
