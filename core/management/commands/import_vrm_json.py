"""Management command to import VRM property listings from a JSON file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from core.integrations.sources.vrm_json_importer import upsert_vrm_records


class Command(BaseCommand):
    """Import VRM property listings from a JSON file (array of records)."""

    help = (
        "Import VRM property listings from a JSON file. "
        "The file must contain a JSON array of VRM property objects."
    )

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "json_file",
            type=str,
            help="Path to the VRM JSON file (array of property records)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        json_path = Path(options["json_file"]).expanduser()
        if not json_path.exists():
            raise CommandError(f"File not found: {json_path}")

        try:
            with json_path.open(encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON: {exc}") from exc

        if isinstance(data, dict):
            # Accept a single object as a one-element list
            data = [data]

        if not isinstance(data, list):
            raise CommandError(
                "JSON file must contain an array of property objects (or a single object)."
            )

        created, updated, errors = upsert_vrm_records(data)

        for error in errors:
            self.stdout.write(self.style.WARNING(f"  Skipped — {error}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete: {created} created, {updated} updated"
                + (f", {len(errors)} skipped" if errors else "")
            )
        )
