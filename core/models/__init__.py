"""Models package — split into domain-focused modules.

Import order matters: modules with fewer dependencies load first.
"""

from __future__ import annotations

# Standalone / low-dependency groups first
from core.models.sources import *  # VrmProperty, HudProperty, UsdaProperty, etc.
from core.models.growth import *  # GrowthArea, MarketSnapshot, etc.
from core.models.notifications import *  # Notification, UserWatchlist, etc.

# Property model (depended on by base and pipeline)
from core.models.property import *  # Property, RentalIncome, etc.

# Depend on Property
from core.models.base import *  # Team, PropertyNote (FK→Property), etc.
from core.models.pipeline import *  # PipelineProperty, PipelineAsset, etc.
