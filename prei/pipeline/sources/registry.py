"""Source registry and factory for discovery-stage data sources.

Provides a single entry point for discovering which sources are available
for a given area, and instantiating them by name.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from prei.pipeline.sources.base import DiscoverySource
from prei.pipeline.sources.county import CountyForeclosureSource
from prei.pipeline.sources.reo_sources import (
    FannieMaeSource,
    HUDHomestoreSource,
    USDAForeclosuresSource,
    VAForeclosuresSource,
)

# ── Built-in source registry ──────────────────────────────────────────────────

_BUILTIN_SOURCES: Dict[str, Type[DiscoverySource]] = {
    "fannie_mae": FannieMaeSource,
    "hud": HUDHomestoreSource,
    "va": VAForeclosuresSource,
    "usda": USDAForeclosuresSource,
    "county": CountyForeclosureSource,
}


def list_sources() -> List[str]:
    """Return names of all registered source types."""
    return list(_BUILTIN_SOURCES.keys())


def get_source(name: str, **kwargs: Any) -> DiscoverySource:
    """Instantiate a discovery source by name.

    Args:
        name: Source name ('fannie_mae', 'hud', 'va', 'usda', 'county').
        **kwargs: Passed to the source constructor.

    Returns:
        An instance of the requested DiscoverySource.

    Raises:
        ValueError: If the source name is not registered.
    """
    cls = _BUILTIN_SOURCES.get(name)
    if cls is None:
        raise ValueError(f"Unknown source '{name}'. Available: {list_sources()}")
    return cls(**kwargs)


def discover_from_all(
    state: str,
    zip_code: Optional[str] = None,
    source_filter: Optional[List[str]] = None,
    **kwargs: Any,
) -> Dict[str, List[Dict[str, Any]]]:
    """Run discovery across multiple sources and return grouped results.

    Args:
        state: Two-letter state code.
        zip_code: Optional ZIP code for geographic narrowing.
        source_filter: Optional list of source names to include.
                       Defaults to all registered sources.
        **kwargs: Additional keyword arguments passed to each source's
                  fetch() method.

    Returns:
        Dict mapping source name → list of raw listing dicts.
    """
    names = source_filter or list_sources()
    results: Dict[str, List[Dict[str, Any]]] = {}

    for name in names:
        try:
            source = get_source(name)
            listings = source.fetch(state, zip_code=zip_code, **kwargs)
            results[name] = listings
        except Exception as exc:
            results[name] = []
            import logging

            logging.getLogger(__name__).error(
                "Source '%s' failed for %s: %s", name, state, exc
            )

    return results
