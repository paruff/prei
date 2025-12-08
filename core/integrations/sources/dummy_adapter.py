from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterable, Dict


def fetch() -> Iterable[Dict]:
    """Return a small set of dummy listings for Phase 1 pipeline testing."""
    base_time = datetime.utcnow()
    return [
        {
            "source": "dummy",
            "address": "123 Main St",
            "city": "Austin",
            "state": "TX",
            "zip_code": "78701",
            "price": Decimal("350000"),
            "beds": 3,
            "baths": Decimal("2.0"),
            "sq_ft": 1500,
            "property_type": "SFH",
            "url": "https://example.com/listings/123-main-st",
            "posted_at": base_time - timedelta(hours=2),
        },
        {
            "source": "dummy",
            "address": "45 Oak Ave",
            "city": "Denver",
            "state": "CO",
            "zip_code": "80203",
            "price": Decimal("525000"),
            "beds": 4,
            "baths": Decimal("2.5"),
            "sq_ft": 2100,
            "property_type": "SFH",
            "url": "https://example.com/listings/45-oak-ave",
            "posted_at": base_time - timedelta(days=1),
        },
    ]
