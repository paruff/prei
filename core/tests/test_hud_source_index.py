"""Tests for HUD Homes for Sale source index discovery."""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management import call_command

from core.integrations.sources.hud_source_index import (
    compute_content_hash,
    diff_source_indexes,
    discover_hud_homes_for_sale_sources,
)

SAMPLE_HTML = """
<html>
  <body>
    <h2>Single Family Homes</h2>
    <ul>
      <li><a href="https://www.va.gov/housing-assistance/home-loans/">Department of Veterans Affairs</a></li>
      <li><a href="/program_offices/housing/sfh/reo">HUD Single Family</a></li>
    </ul>
    <h2>Multifamily Homes</h2>
    <ul>
      <li><a href="https://www.gsaauctions.gov/">General Services Administration</a></li>
      <li><a href="https://www.gsaauctions.gov/?utm_source=hud">General Services Administration</a></li>
    </ul>
  </body>
</html>
"""


def test_discover_hud_source_index_extracts_links_with_provenance() -> None:
    """Discovery returns canonicalized source links with provenance fields."""
    payload_hash = compute_content_hash(SAMPLE_HTML.encode("utf-8"))

    records = discover_hud_homes_for_sale_sources(
        SAMPLE_HTML,
        page_url="https://www.hud.gov/topics/homes_for_sale",
        content_hash=payload_hash,
        retrieved_at="2026-05-07T00:00:00Z",
    )

    assert len(records) == 3
    assert records[0]["category"] == "Single Family Homes"
    assert (
        records[0]["source_url"] == "https://www.va.gov/housing-assistance/home-loans"
    )
    assert (
        records[1]["source_url"]
        == "https://www.hud.gov/program_offices/housing/sfh/reo"
    )
    assert records[2]["category"] == "Multifamily Homes"
    assert records[2]["source_url"] == "https://www.gsaauctions.gov"
    assert all(item["content_hash"] == payload_hash for item in records)
    assert all(item["retrieved_at"] == "2026-05-07T00:00:00Z" for item in records)


def test_diff_source_indexes_reports_added_removed_and_unchanged() -> None:
    """Diff should identify added/removed URLs by canonical source_url."""
    previous = [
        {"source_url": "https://www.va.gov/housing-assistance/home-loans"},
        {"source_url": "https://www.hud.gov/program_offices/housing/sfh/reo"},
    ]
    current = [
        {"source_url": "https://www.va.gov/housing-assistance/home-loans"},
        {"source_url": "https://www.gsaauctions.gov"},
    ]

    diff = diff_source_indexes(previous, current)

    assert diff["added"] == ["https://www.gsaauctions.gov"]
    assert diff["removed"] == ["https://www.hud.gov/program_offices/housing/sfh/reo"]
    assert diff["unchanged"] == ["https://www.va.gov/housing-assistance/home-loans"]


def test_fetch_hud_source_index_command_writes_versioned_files(tmp_path: Path) -> None:
    """Management command writes latest snapshot and diff log from local HTML input."""
    html_path = tmp_path / "hud.html"
    html_path.write_text(SAMPLE_HTML, encoding="utf-8")
    output_dir = tmp_path / "source_index"

    call_command(
        "fetch_hud_source_index",
        "--input-file",
        str(html_path),
        "--output-dir",
        str(output_dir),
    )

    latest_path = output_dir / "latest.json"
    assert latest_path.exists()

    latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
    assert (
        latest_payload["source_page_url"] == "https://www.hud.gov/topics/homes_for_sale"
    )
    assert latest_payload["total_sources"] == 3
    assert latest_payload["sources"][0]["title"] == "Department of Veterans Affairs"

    diff_logs = sorted((output_dir / "diffs").glob("*.json"))
    assert len(diff_logs) == 1
    diff_payload = json.loads(diff_logs[0].read_text(encoding="utf-8"))
    assert diff_payload["counts"]["added"] == 3
    assert diff_payload["counts"]["removed"] == 0
