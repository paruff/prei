"""HUD Homes for Sale source discovery and diff utilities."""

from __future__ import annotations

import hashlib
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

HUD_HOMES_FOR_SALE_URL = "https://www.hud.gov/topics/homes_for_sale"


def fetch_hud_homes_for_sale_html(page_url: str = HUD_HOMES_FOR_SALE_URL) -> bytes:
    """Fetch raw HTML for HUD Homes for Sale index page."""
    request = Request(page_url, headers={"User-Agent": "prei-hud-source-index/1.0"})
    with urlopen(request, timeout=20) as response:
        return response.read()


def compute_content_hash(content: bytes) -> str:
    """Return SHA-256 hash of source content."""
    return hashlib.sha256(content).hexdigest()


def canonicalize_url(url: str) -> str:
    """Normalize URL for stable comparisons."""
    parsed = urlsplit(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    normalized_path = parsed.path.rstrip("/")
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            normalized_path,
            "",
            "",
        )
    )


def discover_hud_homes_for_sale_sources(
    html: str,
    *,
    page_url: str = HUD_HOMES_FOR_SALE_URL,
    retrieved_at: str,
    content_hash: str,
) -> list[dict[str, str]]:
    """Parse HUD source index page into normalized source records."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for anchor in soup.select("a[href]"):
        title = anchor.get_text(strip=True)
        if not title:
            continue
        source_url = canonicalize_url(urljoin(page_url, anchor.get("href", "").strip()))
        if not source_url or source_url in seen_urls:
            continue

        category = _find_closest_heading(anchor)
        seen_urls.add(source_url)
        results.append(
            {
                "title": title,
                "category": category,
                "source_url": source_url,
                "source_domain": urlsplit(source_url).netloc,
                "source_page_url": page_url,
                "retrieved_at": retrieved_at,
                "content_hash": content_hash,
            }
        )

    return results


def diff_source_indexes(
    previous: list[dict[str, Any]],
    current: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """Diff two source index snapshots by canonical source URL."""
    previous_urls = {item["source_url"] for item in previous if item.get("source_url")}
    current_urls = {item["source_url"] for item in current if item.get("source_url")}

    return {
        "added": sorted(current_urls - previous_urls),
        "removed": sorted(previous_urls - current_urls),
        "unchanged": sorted(previous_urls & current_urls),
    }


def _find_closest_heading(anchor: Any) -> str:
    """Find nearest heading text preceding an anchor."""
    for element in anchor.previous_elements:
        name = getattr(element, "name", None)
        if name and name.lower() in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            text = element.get_text(strip=True)
            if text:
                return text
    return "Uncategorized"
