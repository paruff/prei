"""Source adapters for listing ingestion.

Each adapter should implement `fetch()` returning an iterable of normalized dicts:
{
  'source': 'dummy', 'address': '...', 'city': '...', 'state': '...',
  'zip_code': '...', 'price': Decimal, 'beds': int, 'baths': Decimal,
  'sq_ft': int, 'property_type': 'SFH', 'url': 'http...', 'posted_at': datetime
}

Also provides RESO Web API adapter for MLS data feed integration.
"""

from core.integrations.sources.dummy_adapter import fetch as fetch_dummy
from core.integrations.sources.attom_adapter import ATTOMAdapter
from core.integrations.sources.reso_adapter import (
    RESOAdapter,
    RESOAPIError,
    RESOAuthenticationError,
    RESORateLimitError,
    RESOAPIError,
    normalize_property_type,
    normalize_property_data,
)

__all__ = [
    "fetch_dummy",
    "ATTOMAdapter",
    "RESOAdapter",
    "RESOAPIError",
    "RESOAuthenticationError",
    "RESORateLimitError",
    "RESOAPIError",
    "normalize_property_type",
    "normalize_property_data",
]