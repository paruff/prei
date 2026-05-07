from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand

from core.integrations.sources.hud_source_index import (
    HUD_HOMES_FOR_SALE_URL,
    compute_content_hash,
    diff_source_indexes,
    discover_hud_homes_for_sale_sources,
    fetch_hud_homes_for_sale_html,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch HUD Homes for Sale source index and persist versioned snapshot + daily diff"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--output-dir",
            type=str,
            default="data/hud_source_index",
            help="Output directory for index snapshots and diff logs",
        )
        parser.add_argument(
            "--input-file",
            type=str,
            default="",
            help="Optional local HTML file for deterministic runs/testing",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        output_dir = Path(options["output_dir"]).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "diffs").mkdir(parents=True, exist_ok=True)

        raw_html = self._read_html_payload(options.get("input_file", ""))
        content_hash = compute_content_hash(raw_html)
        retrieval_dt = datetime.now(timezone.utc).replace(microsecond=0)
        retrieved_at = retrieval_dt.isoformat()
        safe_timestamp = self._format_timestamp_for_filename(retrieval_dt)

        sources = discover_hud_homes_for_sale_sources(
            raw_html.decode("utf-8", errors="ignore"),
            page_url=HUD_HOMES_FOR_SALE_URL,
            retrieved_at=retrieved_at,
            content_hash=content_hash,
        )

        latest_path = output_dir / "latest.json"
        previous_sources = self._load_previous_sources(latest_path)
        diff = diff_source_indexes(previous_sources, sources)

        payload = {
            "source_page_url": HUD_HOMES_FOR_SALE_URL,
            "retrieved_at": retrieved_at,
            "content_hash": content_hash,
            "total_sources": len(sources),
            "sources": sources,
        }
        version_name = f"{safe_timestamp}-{content_hash[:8]}.json"
        (output_dir / version_name).write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        latest_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        diff_payload = {
            "source_page_url": HUD_HOMES_FOR_SALE_URL,
            "retrieved_at": retrieved_at,
            "content_hash": content_hash,
            "counts": {
                "added": len(diff["added"]),
                "removed": len(diff["removed"]),
                "unchanged": len(diff["unchanged"]),
            },
            "diff": diff,
        }
        diff_path = output_dir / "diffs" / f"{safe_timestamp}.json"
        diff_path.write_text(
            json.dumps(diff_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        self.stdout.write(
            self.style.SUCCESS(
                "HUD source index refreshed. "
                f"total={len(sources)} added={len(diff['added'])} removed={len(diff['removed'])}"
            )
        )

    def _read_html_payload(self, input_file: str) -> bytes:
        if input_file:
            return Path(input_file).read_bytes()
        return fetch_hud_homes_for_sale_html()

    def _load_previous_sources(self, latest_path: Path) -> list[dict[str, str]]:
        if not latest_path.exists():
            return []
        try:
            payload: Any = json.loads(latest_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return []

            raw_sources: Any = payload.get("sources", [])
            if not isinstance(raw_sources, list):
                return []

            normalized_sources: list[dict[str, str]] = []
            for source in raw_sources:
                if not isinstance(source, dict):
                    continue
                normalized_source = {
                    str(key): str(value)
                    for key, value in source.items()
                    if isinstance(key, str) and isinstance(value, str)
                }
                if normalized_source.get("source_url"):
                    normalized_sources.append(normalized_source)

            return normalized_sources
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Failed to load previous HUD source index snapshot: %s (%s: %s)",
                latest_path,
                type(exc).__name__,
                exc,
                exc_info=True,
            )
            return []

    def _format_timestamp_for_filename(self, timestamp: datetime) -> str:
        return timestamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
