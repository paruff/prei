"""Models package — split into domain-focused modules.

Import order matters: modules with fewer dependencies load first.
"""
from __future__ import annotations

# ── Standalone / low-dependency groups first ──
from core.models.sources import *  # noqa: F403  # VrmProperty, HudProperty, etc.
from core.models.growth import *  # noqa: F403  # GrowthArea, MarketSnapshot, etc.
from core.models.notifications import *  # noqa: F403  # Notification, UserWatchlist, etc.

# ── Property model (depended on by base and pipeline) ──
from core.models.property import *  # noqa: F403  # Property, RentalIncome, etc.

# ── Depend on Property ──
from core.models.base import *  # noqa: F403  # Team, PropertyNote, etc.
from core.models.pipeline import *  # noqa: F403  # PipelineProperty, etc.
