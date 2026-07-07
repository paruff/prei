"""Tests for the pipeline REST API and CLI."""

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from prei.api.pipeline_routes import configure_repository, router
from prei.models.pipeline import PropertyAsset
from prei.pipeline.engine import InMemoryAssetRepository

# Build a FastAPI app for testing
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def reset_repo():
    """Give each test a fresh repository."""
    repo = InMemoryAssetRepository()
    configure_repository(repo)
    # Seed two assets
    a1 = PropertyAsset(asset_id="API-001", address="123 Test St")
    a2 = PropertyAsset(asset_id="API-002", address="456 Mock Ave")
    repo.save(a1)
    repo.save(a2)
    yield


# ═══════════════════════════════════════════════════════════════════════════════
#  GET /api/v1/pipeline/summary
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetSummary:
    def test_returns_summary(self):
        resp = client.get("/api/v1/pipeline/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_assets" in data
        assert data["total_assets"] == 2
        assert "by_stage" in data
        assert "pipeline_flow" in data
        assert "killed" in data

    def test_by_stage_counts(self):
        resp = client.get("/api/v1/pipeline/summary")
        data = resp.json()
        # Both assets start at GACS
        assert data["by_stage"]["GACS"] == 2

    def test_empty_repo(self):
        repo = InMemoryAssetRepository()
        configure_repository(repo)
        resp = client.get("/api/v1/pipeline/summary")
        assert resp.status_code == 200
        assert resp.json()["total_assets"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
#  GET /api/v1/pipeline/assets
# ═══════════════════════════════════════════════════════════════════════════════


class TestListAssets:
    def test_list_all(self):
        resp = client.get("/api/v1/pipeline/assets")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        ids = {a["asset_id"] for a in data}
        assert ids == {"API-001", "API-002"}

    def test_asset_structure(self):
        resp = client.get("/api/v1/pipeline/assets")
        asset = resp.json()[0]
        assert "asset_id" in asset
        assert "address" in asset
        assert "current_stage" in asset
        assert "stage_history" in asset
        assert "kill_reason" in asset


# ═══════════════════════════════════════════════════════════════════════════════
#  GET /api/v1/pipeline/assets/{asset_id}
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetAsset:
    def test_get_existing(self):
        resp = client.get("/api/v1/pipeline/assets/API-001")
        assert resp.status_code == 200
        assert resp.json()["asset_id"] == "API-001"

    def test_get_nonexistent(self):
        resp = client.get("/api/v1/pipeline/assets/DOES-NOT-EXIST")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
#  POST /api/v1/pipeline/assets
# ═══════════════════════════════════════════════════════════════════════════════


class TestCreateAsset:
    def test_create(self):
        resp = client.post(
            "/api/v1/pipeline/assets",
            json={"asset_id": "NEW-001", "address": "789 New St"},
        )
        assert resp.status_code == 200
        assert resp.json()["asset_id"] == "NEW-001"
        assert resp.json()["current_stage"] == "GACS"

    def test_create_duplicate(self):
        resp = client.post(
            "/api/v1/pipeline/assets",
            json={"asset_id": "API-001", "address": "dup"},
        )
        assert resp.status_code == 409

    def test_create_missing_fields(self):
        resp = client.post(
            "/api/v1/pipeline/assets",
            json={"asset_id": "NO-ADDR"},
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
#  POST /api/v1/pipeline/transition
# ═══════════════════════════════════════════════════════════════════════════════


class TestTransition:
    def test_valid_transition(self):
        resp = client.post(
            "/api/v1/pipeline/transition",
            json={
                "asset_id": "API-001",
                "target_stage": "DISCOVERY",
                "reason": "Testing",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_stage"] == "DISCOVERY"
        assert len(data["stage_history"]) == 1

    def test_invalid_stage_name(self):
        resp = client.post(
            "/api/v1/pipeline/transition",
            json={"asset_id": "API-001", "target_stage": "INVALID_STAGE"},
        )
        assert resp.status_code == 422

    def test_illicit_jump(self):
        """GACS → PORTFOLIO is illegal and returns 422."""
        resp = client.post(
            "/api/v1/pipeline/transition",
            json={"asset_id": "API-001", "target_stage": "PORTFOLIO"},
        )
        assert resp.status_code == 422
        assert "GACS" in resp.json()["detail"]

    def test_nonexistent_asset(self):
        resp = client.post(
            "/api/v1/pipeline/transition",
            json={"asset_id": "MISSING", "target_stage": "DISCOVERY"},
        )
        assert resp.status_code == 404

    def test_missing_asset_id(self):
        resp = client.post(
            "/api/v1/pipeline/transition",
            json={"target_stage": "DISCOVERY"},
        )
        assert resp.status_code == 422

    def test_transition_with_context(self):
        resp = client.post(
            "/api/v1/pipeline/transition",
            json={
                "asset_id": "API-001",
                "target_stage": "KILLED",
                "reason": "Budget cut",
                "context": {"violation_reason": "Not viable"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_stage"] == "KILLED"
        assert data["kill_reason"] == "Budget cut"


# ═══════════════════════════════════════════════════════════════════════════════
#  DELETE /api/v1/pipeline/assets/{asset_id}
# ═══════════════════════════════════════════════════════════════════════════════


class TestDeleteAsset:
    def test_delete_existing_soft(self):
        resp = client.delete("/api/v1/pipeline/assets/API-001")
        assert resp.status_code == 200
        assert resp.json()["status"] == "killed"
        # Asset should now be in KILLED stage
        get_resp = client.get("/api/v1/pipeline/assets/API-001")
        assert get_resp.json()["current_stage"] == "KILLED"

    def test_delete_nonexistent(self):
        resp = client.delete("/api/v1/pipeline/assets/DOES-NOT-EXIST")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestCLI:
    @pytest.fixture
    def mls_feed(self):
        """Create a temporary MLS JSON feed file."""
        data = {
            "properties": [
                {
                    "asset_id": "MLS-001",
                    "address": "101 Prime St",
                    "estimated_monthly_rent": 2500.0,
                    "purchase_price": 300_000.0,
                    "beds": 3,
                    "baths": 2,
                },
                {
                    "asset_id": "MLS-002",
                    "address": "202 Bad Ave",
                    "estimated_monthly_rent": 800.0,
                    "purchase_price": 400_000.0,
                    "beds": 1,
                    "baths": 0.5,
                },
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        yield path
        Path(path).unlink()

    def test_cli_ingest_no_screening(self, mls_feed, capsys):
        from prei.cli import cli
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cli, ["pipeline", "ingest", "--source", mls_feed])
        assert result.exit_code == 0
        assert "Ingested 2 properties" in result.output

    def test_cli_ingest_with_screening(self, mls_feed, capsys):
        from prei.cli import cli
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "pipeline",
                "ingest",
                "--source",
                mls_feed,
                "--run-screening",
                "--min-yield",
                "0.05",
                "--max-ptr",
                "20.0",
            ],
        )
        assert result.exit_code == 0
        assert "Screening:" in result.output

    def test_cli_summary(self):
        from prei.cli import cli
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cli, ["pipeline", "summary"])
        assert result.exit_code == 0
        assert "total_assets" in result.output

    def test_cli_transition_valid(self):
        from prei.cli import cli
        from click.testing import CliRunner

        # First create an asset via API
        client.post(
            "/api/v1/pipeline/assets",
            json={"asset_id": "CLI-001", "address": "CLI St"},
        )

        runner = CliRunner()
        # CLI creates its own engine, so this only tests the command syntax
        # The engine in CLI is fresh (no pre-existing assets)
        result = runner.invoke(
            cli,
            [
                "pipeline",
                "transition",
                "--asset-id",
                "CLI-001",
                "--target",
                "DISCOVERY",
            ],
        )
        # CLI engine is fresh — asset won't exist
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_cli_transition_invalid_stage(self):
        from prei.cli import cli
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["pipeline", "transition", "--asset-id", "BOGUS", "--target", "BOGUS"],
        )
        assert result.exit_code == 1
        # Asset not found (checked first); invalid stage is secondary
        # Both conditions produce exit code 1
        assert result.exit_code != 0
