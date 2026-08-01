"""Base abstractions for discovery-stage data sources.

Each source adapter implements the DiscoverySource ABC and returns
raw listing dicts compatible with DiscoverySanitizer.transform_input().
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class DiscoverySource(ABC):
    """Abstract base for a property discovery data source.

    Subclasses implement fetch() to return raw listing dicts from an
    external API, scrape, or file feed. The output dicts should have
    keys compatible with DiscoverySanitizer.transform_input().

    All sources filter by state; zip_code is optional for sources that
    support geographic narrowing.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable source label (e.g. 'fannie_mae', 'hud')."""
        ...

    @abstractmethod
    def fetch(
        self,
        state: str,
        zip_code: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Fetch raw property listings from this source.

        Args:
            state: Two-letter US state code (e.g. 'CA', 'TX').
            zip_code: Optional 5-digit ZIP code for geographic narrowing.
            **kwargs: Source-specific parameters (page, limit, status, etc.).

        Returns:
            List of raw dicts, each containing at minimum address
            and price keys compatible with transform_input().
        """
        ...
