"""State landlord-friendliness scoring for the Growth Area Explorer.

Scores are on a 0-10 scale:
  0-3 = Tenant-Friendly (red)
  4-6 = Neutral (yellow)
  7-10 = Landlord-Friendly (green)

Based on: eviction speed, rent control, deposit caps, regulatory burden.
Sources: Nolo.com, Intelligent Landlord Index, local state statutes 2026.
"""

STATE_LANDLORD_FRIENDLINESS: dict[str, dict[str, object]] = {
    # 🟩 Most Landlord-Friendly (7-10)
    "TX": {"score": 9, "label": "Landlord-Friendly", "tier": "top"},
    "FL": {"score": 8, "label": "Landlord-Friendly", "tier": "top"},
    "IN": {"score": 8, "label": "Landlord-Friendly", "tier": "top"},
    "TN": {"score": 8, "label": "Landlord-Friendly", "tier": "top"},
    "GA": {"score": 8, "label": "Landlord-Friendly", "tier": "top"},
    "AL": {"score": 9, "label": "Landlord-Friendly", "tier": "top"},
    "AZ": {"score": 7, "label": "Landlord-Friendly", "tier": "top"},
    "AR": {"score": 8, "label": "Landlord-Friendly", "tier": "top"},
    "LA": {"score": 7, "label": "Landlord-Friendly", "tier": "top"},
    "ID": {"score": 7, "label": "Landlord-Friendly", "tier": "top"},
    "MS": {"score": 7, "label": "Landlord-Friendly", "tier": "top"},
    "SC": {"score": 7, "label": "Landlord-Friendly", "tier": "top"},
    "KY": {"score": 7, "label": "Landlord-Friendly", "tier": "top"},
    "OK": {"score": 7, "label": "Landlord-Friendly", "tier": "top"},
    "WV": {"score": 7, "label": "Landlord-Friendly", "tier": "top"},
    "WY": {"score": 7, "label": "Landlord-Friendly", "tier": "top"},
    # 🟥 Most Tenant-Friendly (0-3)
    "CA": {"score": 1, "label": "Tenant-Friendly", "tier": "bottom"},
    "NY": {"score": 1, "label": "Tenant-Friendly", "tier": "bottom"},
    "OR": {"score": 2, "label": "Tenant-Friendly", "tier": "bottom"},
    "NJ": {"score": 1, "label": "Tenant-Friendly", "tier": "bottom"},
    "MA": {"score": 1, "label": "Tenant-Friendly", "tier": "bottom"},
    "DC": {"score": 0, "label": "Tenant-Friendly", "tier": "bottom"},
    "HI": {"score": 2, "label": "Tenant-Friendly", "tier": "bottom"},
    "MD": {"score": 2, "label": "Tenant-Friendly", "tier": "bottom"},
    "CT": {"score": 2, "label": "Tenant-Friendly", "tier": "bottom"},
    "CO": {"score": 3, "label": "Tenant-Friendly", "tier": "bottom"},
    "WA": {"score": 3, "label": "Tenant-Friendly", "tier": "bottom"},
    "IL": {"score": 3, "label": "Tenant-Friendly", "tier": "bottom"},
    "MN": {"score": 3, "label": "Tenant-Friendly", "tier": "bottom"},
    "VT": {"score": 3, "label": "Tenant-Friendly", "tier": "bottom"},
    # 🟨 Neutral (4-6) — everything else
    "OH": {"score": 6, "label": "Neutral", "tier": "middle"},
    "MI": {"score": 5, "label": "Neutral", "tier": "middle"},
    "NC": {"score": 6, "label": "Neutral", "tier": "middle"},
    "VA": {"score": 5, "label": "Neutral", "tier": "middle"},
    "PA": {"score": 5, "label": "Neutral", "tier": "middle"},
    "MO": {"score": 5, "label": "Neutral", "tier": "middle"},
    "WI": {"score": 4, "label": "Neutral", "tier": "middle"},
    "NV": {"score": 5, "label": "Neutral", "tier": "middle"},
    "UT": {"score": 6, "label": "Neutral", "tier": "middle"},
    "NM": {"score": 4, "label": "Neutral", "tier": "middle"},
    "NE": {"score": 6, "label": "Neutral", "tier": "middle"},
    "KS": {"score": 6, "label": "Neutral", "tier": "middle"},
    "IA": {"score": 5, "label": "Neutral", "tier": "middle"},
    "SD": {"score": 6, "label": "Neutral", "tier": "middle"},
    "ND": {"score": 6, "label": "Neutral", "tier": "middle"},
    "MT": {"score": 5, "label": "Neutral", "tier": "middle"},
    "AK": {"score": 5, "label": "Neutral", "tier": "middle"},
    "DE": {"score": 4, "label": "Neutral", "tier": "middle"},
    "ME": {"score": 4, "label": "Neutral", "tier": "middle"},
    "NH": {"score": 5, "label": "Neutral", "tier": "middle"},
    "RI": {"score": 4, "label": "Neutral", "tier": "middle"},
}


def get_state_landlord_score(state: str) -> dict[str, object]:
    """Return landlord-friendliness data for a state code."""
    return STATE_LANDLORD_FRIENDLINESS.get(
        state.upper(),
        {"score": 5, "label": "Unknown", "tier": "middle"},
    )
