"""Source adapters for listing ingestion.

Each adapter should implement `fetch()` returning an iterable of normalized dicts:
{
  'source': 'dummy', 'address': '...', 'city': '...', 'state': '...',
  'zip_code': '...', 'price': Decimal, 'beds': int, 'baths': Decimal,
  'sq_ft': int, 'property_type': 'SFH', 'url': 'http...', 'posted_at': datetime
}
"""
