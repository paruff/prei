"""Source adapters for listing ingestion.

Each adapter should implement `fetch()` returning an iterable of normalized dicts:
{
  'source': 'dummy', 'address': '...', 'city': '...', 'state': '...',
  'zip_code': '...', 'price': Decimal, 'beds': int, 'baths': Decimal,
  'sq_ft': int, 'property_type': 'SFH', 'url': 'http...', 'posted_at': datetime
}

The RESO Web API adapter (MLS data feed) lives in
``core.integrations.sources.reso_adapter`` — import it directly:

    from core.integrations.sources.reso_adapter import RESOAdapter
"""

__all__ = ["reso_adapter", "attom_adapter", "dummy_adapter"]
