"""Tests for VRM JSON import — importer utility, API endpoint, and management command."""

from __future__ import annotations

import json
import io
from decimal import Decimal

from django.test import TestCase, Client

from core.models import VrmProperty
from core.integrations.sources.vrm_json_importer import (
    parse_vrm_json_record,
    upsert_vrm_records,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

RECORD_FOR_SALE = {
    "state": "VA",
    "city": "VIRGINIA BEACH",
    "county": "VIRGINIA BEACH CITY",
    "zip": "23462",
    "address": "5612 SUMMIT ARCH",
    "asset_id": 28664,
    "asset_reference_id": "224858",
    "status": "For Sale",
    "list_price": 119000.0,
    "sqft": 793,
    "bedrooms": 2,
    "bathrooms": 1.0,
    "lot_size": 11.51,
    "lot_size_source": "ac",
    "property_type": "Condo",
    "is_vendee_financing": False,
    "is_auction": False,
    "url": "https://www.vrmproperties.com/Property-For-Sale/28664/virginia-beach-va-23462",
    "media_guid": "772574bb-83a7-4626-8440-39e19da96b43",
    "is_new_listing": True,
    "asset_start_date": "2026-06-16T16:19:40.8562374",
    "listing_start_date": "2026-06-16T16:19:40.8812831",
}

RECORD_VENDEE = {
    "state": "VA",
    "city": "GREENBACKVILLE",
    "county": "ACCOMACK",
    "zip": "23356",
    "address": "2402 OCTOPUS RD",
    "asset_id": 27902,
    "asset_reference_id": "208509",
    "status": "For Sale",
    "list_price": 242000.0,
    "sqft": 1815,
    "bedrooms": 4,
    "bathrooms": 2.0,
    "lot_size": 9750.0,
    "lot_size_source": "SF",
    "property_type": "Single Family",
    "is_vendee_financing": True,
    "is_auction": False,
    "url": "https://www.vrmproperties.com/Property-For-Sale/27902/greenbackville-va-23356",
    "media_guid": "71b39924-a5b9-4071-b5a1-dc58ea647ada",
    "is_new_listing": False,
    "asset_start_date": "2026-05-19T10:38:12.1492925",
    "listing_start_date": "2026-05-19T10:38:12.5344191",
}

# ---------------------------------------------------------------------------
# parse_vrm_json_record unit tests
# ---------------------------------------------------------------------------


class ParseVrmJsonRecordTest(TestCase):
    def test_basic_field_mapping(self):
        result = parse_vrm_json_record(RECORD_FOR_SALE)
        self.assertEqual(result["vrm_property_id"], 28664)
        self.assertEqual(result["vrm_listing_url"], RECORD_FOR_SALE["url"])
        self.assertEqual(result["address"], "5612 Summit Arch")
        self.assertEqual(result["city"], "Virginia Beach")
        self.assertEqual(result["state"], "VA")
        self.assertEqual(result["zip_code"], "23462")
        self.assertEqual(result["county"], "VIRGINIA BEACH CITY")
        self.assertEqual(result["list_price"], Decimal("119000.0"))
        self.assertEqual(result["square_feet"], 793)
        self.assertEqual(result["bedrooms"], 2)
        self.assertEqual(result["bathrooms"], Decimal("1.0"))
        self.assertEqual(result["property_type"], "Condo")
        self.assertEqual(result["status"], VrmProperty.Status.FOR_SALE)
        self.assertEqual(result["listing_type"], VrmProperty.ListingType.TRADITIONAL)
        self.assertFalse(result["vendee_eligible"])

    def test_lot_size_acres_converted_to_sf(self):
        result = parse_vrm_json_record(RECORD_FOR_SALE)
        # 11.51 ac * 43560 = 501,376 sf (rounded down)
        self.assertEqual(
            result["lot_size_sf"], int(Decimal("11.51") * Decimal("43560"))
        )

    def test_lot_size_sf_passthrough(self):
        result = parse_vrm_json_record(RECORD_VENDEE)
        self.assertEqual(result["lot_size_sf"], 9750)

    def test_vendee_financing_flag(self):
        result = parse_vrm_json_record(RECORD_VENDEE)
        self.assertTrue(result["vendee_eligible"])

    def test_auction_listing_type(self):
        record = dict(RECORD_FOR_SALE, is_auction=True, asset_id=99001)
        result = parse_vrm_json_record(record)
        self.assertEqual(result["listing_type"], VrmProperty.ListingType.ONLINE_AUCTION)

    def test_missing_asset_id_raises(self):
        record = dict(RECORD_FOR_SALE)
        del record["asset_id"]
        with self.assertRaises(ValueError, msg="asset_id"):
            parse_vrm_json_record(record)

    def test_missing_url_raises(self):
        record = dict(RECORD_FOR_SALE, url="")
        with self.assertRaises(ValueError, msg="url"):
            parse_vrm_json_record(record)

    def test_status_normalization(self):
        for raw, expected in [
            ("For Sale", VrmProperty.Status.FOR_SALE),
            ("Coming Soon", VrmProperty.Status.COMING_SOON),
            ("Pending", VrmProperty.Status.PENDING),
            ("Sold", VrmProperty.Status.SOLD),
            ("Unknown", VrmProperty.Status.FOR_SALE),
        ]:
            result = parse_vrm_json_record(
                dict(RECORD_FOR_SALE, status=raw, asset_id=99900)
            )
            self.assertEqual(result["status"], expected, msg=f"status={raw!r}")

    def test_null_optional_fields(self):
        record = dict(
            RECORD_FOR_SALE,
            asset_id=99002,
            list_price=None,
            sqft=None,
            bedrooms=None,
            bathrooms=None,
            lot_size=None,
            county=None,
            property_type=None,
        )
        result = parse_vrm_json_record(record)
        self.assertIsNone(result["list_price"])
        self.assertIsNone(result["square_feet"])
        self.assertIsNone(result["bedrooms"])
        self.assertIsNone(result["bathrooms"])
        self.assertIsNone(result["lot_size_sf"])
        self.assertIsNone(result["county"])
        self.assertIsNone(result["property_type"])


# ---------------------------------------------------------------------------
# upsert_vrm_records integration tests
# ---------------------------------------------------------------------------


class UpsertVrmRecordsTest(TestCase):
    def test_creates_new_records(self):
        created, updated, errors = upsert_vrm_records([RECORD_FOR_SALE, RECORD_VENDEE])
        self.assertEqual(created, 2)
        self.assertEqual(updated, 0)
        self.assertEqual(errors, [])
        self.assertEqual(VrmProperty.objects.count(), 2)

    def test_updates_existing_record(self):
        upsert_vrm_records([RECORD_FOR_SALE])
        modified = dict(RECORD_FOR_SALE, list_price=130000.0)
        created, updated, errors = upsert_vrm_records([modified])
        self.assertEqual(created, 0)
        self.assertEqual(updated, 1)
        prop = VrmProperty.objects.get(vrm_property_id=28664)
        self.assertEqual(prop.list_price, Decimal("130000.0"))

    def test_preserves_original_scraped_at(self):
        upsert_vrm_records([RECORD_FOR_SALE])
        original_scraped = VrmProperty.objects.get(vrm_property_id=28664).scraped_at
        upsert_vrm_records([RECORD_FOR_SALE])
        after_scraped = VrmProperty.objects.get(vrm_property_id=28664).scraped_at
        self.assertEqual(original_scraped, after_scraped)

    def test_bad_record_returns_error_skips_record(self):
        bad = dict(RECORD_FOR_SALE)
        del bad["asset_id"]
        created, updated, errors = upsert_vrm_records([bad, RECORD_VENDEE])
        self.assertEqual(created, 1)
        self.assertEqual(len(errors), 1)
        self.assertIn("asset_id", errors[0])

    def test_single_dict_accepted(self):
        # Callers may pass a list with one item
        created, updated, errors = upsert_vrm_records([RECORD_FOR_SALE])
        self.assertEqual(created, 1)


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class VrmPropertyImportAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = "/api/v1/vrm-properties/import/"

    def _post_json(self, payload):
        return self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN="test",
        )

    def _post_file(self, payload):
        file_content = json.dumps(payload).encode()
        uploaded = io.BytesIO(file_content)
        uploaded.name = "vrm_export.json"
        return self.client.post(
            self.url,
            data={"file": uploaded},
            format="multipart",
        )

    def test_import_array_via_json_body(self):
        resp = self._post_json([RECORD_FOR_SALE, RECORD_VENDEE])
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["created"], 2)
        self.assertEqual(data["updated"], 0)
        self.assertEqual(data["skipped"], 0)

    def test_import_single_object_via_json_body(self):
        resp = self._post_json(RECORD_FOR_SALE)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["created"], 1)

    def test_import_via_file_upload(self):
        resp = self._post_file([RECORD_FOR_SALE, RECORD_VENDEE])
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["created"], 2)

    def test_empty_array_returns_400(self):
        resp = self._post_json([])
        self.assertEqual(resp.status_code, 400)

    def test_invalid_json_string_returns_400(self):
        resp = self.client.post(
            self.url,
            data="not-json",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_partial_errors_return_207(self):
        bad = dict(RECORD_FOR_SALE)
        del bad["asset_id"]
        resp = self._post_json([bad, RECORD_VENDEE])
        self.assertEqual(resp.status_code, 207)
        data = resp.json()
        self.assertEqual(data["created"], 1)
        self.assertEqual(data["skipped"], 1)
        self.assertEqual(len(data["errors"]), 1)

    def test_idempotent_reimport(self):
        self._post_json([RECORD_FOR_SALE])
        resp = self._post_json([RECORD_FOR_SALE])
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["created"], 0)
        self.assertEqual(data["updated"], 1)
