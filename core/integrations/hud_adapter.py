from typing import List, Dict, Optional
import os


def is_enabled() -> bool:
    return os.getenv("HUD_ENABLED", "false").lower() in {"1", "true", "yes"}


def fetch_properties(state: Optional[str] = None, zip_code: Optional[str] = None) -> List[Dict]:
    """Fetch HUD properties for a given area.

    This is a scaffold. When `HUD_ENABLED` is true, integrate real HUD API/feed.
    Returns a list of dicts with keys: address, city, state, zip_code, price, beds, baths, sq_ft, url.
    """
    if not is_enabled():
        # Return empty when not enabled; avoids confusing mixed sources
        return []

    # TODO: Implement real HUD integration. For now, minimal mock to demonstrate flow.
    demo = [
        {
            "address": "123 HUD Ave",
            "city": "Sample",
            "state": state or "TX",
            "zip_code": zip_code or "78701",
            "price": 225000,
            "beds": 3,
            "baths": 2,
            "sq_ft": 1450,
            "url": "https://www.hud.gov/homes/sample",
        }
    ]
    return demo
