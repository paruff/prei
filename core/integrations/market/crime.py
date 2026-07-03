"""Crime data adapter — currently a placeholder.

SPIKE finding (TASK-A1, 2026-07-03):
  The FBI Crime Data Explorer (CDE) API is gated behind api.data.gov, which
  requires a registered API key. Attempts to access the base URL
  https://api.usa.gov/crime/fbi/cde/ returned HTTP 403, confirming key-gated
  access. Registration details and rate-limit policies were not obtainable
  without an active key.

  Until a confirmed, reliable crime-data API source is identified and its
  auth / rate-limit / geography-level constraints are verified, this adapter
  produces state-based dummy values only.

  DECISION-2, Option C is recommended: keep the dummy and relabel it clearly
  in UIs as "placeholder" rather than presenting it as live data.

  The existing ``get_crime_score`` function is intentionally left unchanged
  for backward compatibility — callers in ``market_data.py`` and elsewhere
  are unaffected.
"""

from decimal import Decimal


def get_crime_score(
    zip_code: str | None = None, city: str | None = None, state: str | None = None
) -> Decimal:
    """Return a placeholder crime score (lower is better).

    This is a state-based dummy.  No live API integration is available.
    See module docstring above for context.
    """
    base = Decimal("3.0")
    if state == "TX":
        base = Decimal("2.5")
    if state == "CA":
        base = Decimal("3.5")
    return base
