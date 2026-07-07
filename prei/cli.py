"""CLI tool for the property pipeline.

Usage:
    prei-cli pipeline summary
    prei-cli pipeline ingest --source mls_feed.json --run-screening
    prei-cli pipeline transition --asset-id ASSET-001 --target UNDERWRITING
"""

from __future__ import annotations

import json
import sys

import click

from prei.models.pipeline import InvalidStageTransitionException, PipelineStage
from prei.pipeline.engine import (
    InMemoryAssetRepository,
    PipelineEngine,
    StateAggregator,
)
from prei.pipeline.handlers.batch_screening import BatchScreeningProcessor
from prei.pipeline.handlers.screening import ScreeningThresholds


# ── Shared engine factory ─────────────────────────────────────────────────────


def _make_engine() -> PipelineEngine:
    """Create a fresh engine with in-memory repository."""
    return PipelineEngine(repository=InMemoryAssetRepository())


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI group
# ═══════════════════════════════════════════════════════════════════════════════


@click.group()
def cli() -> None:
    """PREI pipeline management CLI."""


# ═══════════════════════════════════════════════════════════════════════════════
#  pipeline summary
# ═══════════════════════════════════════════════════════════════════════════════


@cli.group()
def pipeline() -> None:
    """Pipeline state machine commands."""


@pipeline.command()
def summary() -> None:
    """Print aggregate pipeline stats."""
    engine = _make_engine()
    aggregator = StateAggregator(engine.repository)
    data = aggregator.summary()
    click.echo(json.dumps(data, indent=2))


# ═══════════════════════════════════════════════════════════════════════════════
#  pipeline ingest
# ═══════════════════════════════════════════════════════════════════════════════


@pipeline.command()
@click.option(
    "--source",
    "-s",
    required=True,
    type=click.Path(exists=True),
    help="Path to JSON file with property payloads",
)
@click.option(
    "--run-screening",
    is_flag=True,
    default=False,
    help="Run screening evaluation after ingest",
)
@click.option(
    "--min-yield",
    default=0.07,
    type=float,
    help="Minimum gross yield threshold (default 0.07)",
)
@click.option(
    "--max-ptr",
    default=15.0,
    type=float,
    help="Maximum price-to-rent ratio (default 15.0)",
)
def ingest(source: str, run_screening: bool, min_yield: float, max_ptr: float) -> None:
    """Ingest properties from a JSON file and optionally run screening."""
    with open(source, "r") as f:
        data = json.load(f)

    # Support both list and {"properties": [...]} formats
    if isinstance(data, dict):
        payloads = data.get("properties", data.get("assets", []))
    else:
        payloads = data

    if not payloads:
        click.echo("No properties found in source file.", err=True)
        sys.exit(1)

    engine = _make_engine()
    click.echo(f"Ingested {len(payloads)} properties from {source}")

    # Save each property as an asset
    for p in payloads:
        asset_id = p.get("asset_id", p.get("id", f"auto-{hash(str(p))}"))
        address = p.get("address", "Unknown")
        engine.repository.save(
            __import__(
                "prei.models.pipeline", fromlist=["PropertyAsset"]
            ).PropertyAsset(asset_id=asset_id, address=address)
        )

    if run_screening:
        thresholds = ScreeningThresholds(
            min_gross_yield=min_yield,
            max_price_to_rent_ratio=max_ptr,
            min_beds=p["beds"] if "beds" in (p for p in payloads) else 1,
            min_baths=1,
        )
        processor = BatchScreeningProcessor(engine, thresholds)
        result = processor.process(payloads)
        click.echo(
            f"Screening: {result['processed']} processed, "
            f"{result['advanced']} advanced, "
            f"{result['killed']} killed "
            f"in {result['execution_time_ms']:.1f}ms"
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  pipeline transition
# ═══════════════════════════════════════════════════════════════════════════════


@pipeline.command()
@click.option("--asset-id", "-a", required=True, help="Asset identifier")
@click.option("--target", "-t", required=True, help="Target pipeline stage")
@click.option("--reason", "-r", default=None, help="Transition reason")
def transition(asset_id: str, target: str, reason: str | None) -> None:
    """Force a manual stage transition for an asset."""
    engine = _make_engine()

    asset = engine.repository.load(asset_id)
    if asset is None:
        click.echo(f"Error: Asset '{asset_id}' not found.", err=True)
        sys.exit(1)

    try:
        target_stage = PipelineStage(target.upper())
    except ValueError:
        valid = [s.value for s in PipelineStage]
        click.echo(
            f"Invalid stage '{target}'. Valid values: {valid}",
            err=True,
        )
        sys.exit(1)

    try:
        updated = engine.process_transition(
            asset,
            target_stage,
            {"reason": reason or f"CLI transition to {target_stage.value}"},
        )
    except InvalidStageTransitionException as exc:
        click.echo(f"Transition failed: {exc}", err=True)
        sys.exit(1)

    click.echo(
        f"Asset {asset_id}: {updated.current_stage.value} "
        f"(history: {len(updated.stage_history)} transitions)"
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    cli()
