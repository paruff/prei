"""Tests for VRM Properties API and serializer."""

from __future__ import annotations

from decimal import Decimal
from django.utils import timezone

from django.test import TestCase, Client

from core.models import VrmProperty
from core.serializers import VrmPropertySerializer


class VrmPropertySerializerTest(TestCase):
    """Tests for VrmPropertySerializer."""

    def setUp(self):
        self.prop = VrmProperty.objects.create(
            vrm_property_id=99999,
            vrm_listing_url="https://vrmproperties.com/Property-For-Sale/99999/test",
            address="123 TEST ST",
            city="TESTVILLE",
            state="VA",
            zip_code="12345",
            county="TEST COUNTY",
            list_price=Decimal("250000.00"),
            bedrooms=3,
            bathrooms=Decimal("2.0"),
            square_feet=1500,
            status="for_sale",
            vendee_eligible=True,
            scraped_at=timezone.now(),
            last_seen_at=timezone.now(),
        )

    def test_serialize_all_fields(self):
        data = VrmPropertySerializer(self.prop).data
        self.assertEqual(data["vrm_property_id"], 99999)
        self.assertEqual(data["address"], "123 TEST ST")
        self.assertEqual(data["city"], "TESTVILLE")
        self.assertEqual(data["state"], "VA")
        self.assertEqual(data["zip_code"], "12345")
        self.assertEqual(data["list_price"], "250000.00")
        self.assertEqual(data["bedrooms"], 3)
        self.assertTrue(data["vendee_eligible"])

    def test_serialize_nullable_fields(self):
        prop = VrmProperty.objects.create(
            vrm_property_id=99998,
            vrm_listing_url="https://vrmproperties.com/Property-For-Sale/99998/test",
            address="456 NULL ST",
            city="NULLVILLE",
            state="CA",
            zip_code="90210",
            list_price=None,
            bedrooms=None,
            bathrooms=None,
            square_feet=None,
            status="for_sale",
            vendee_eligible=False,
            scraped_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        data = VrmPropertySerializer(prop).data
        self.assertIsNone(data["list_price"])
        self.assertIsNone(data["bedrooms"])
        self.assertIsNone(data["bathrooms"])
        self.assertIsNone(data["square_feet"])


class VrmPropertyListAPITest(TestCase):
    """Tests for GET /api/v1/vrm-properties/."""

    def setUp(self):
        self.client = Client()
        self.url = "/api/v1/vrm-properties/"
        now = timezone.now()
        VrmProperty.objects.create(
            vrm_property_id=10001,
            vrm_listing_url="https://vrmproperties.com/Property-For-Sale/10001/test",
            address="100 MAIN ST",
            city="RICHMOND",
            state="VA",
            zip_code="23220",
            list_price=Decimal("200000.00"),
            status="for_sale",
            vendee_eligible=True,
            scraped_at=now,
            last_seen_at=now,
        )
        VrmProperty.objects.create(
            vrm_property_id=10002,
            vrm_listing_url="https://vrmproperties.com/Property-For-Sale/10002/test",
            address="200 OAK AVE",
            city="NORFOLK",
            state="VA",
            zip_code="23505",
            list_price=Decimal("180000.00"),
            status="for_sale",
            vendee_eligible=False,
            scraped_at=now,
            last_seen_at=now,
        )
        VrmProperty.objects.create(
            vrm_property_id=10003,
            vrm_listing_url="https://vrmproperties.com/Property-For-Sale/10003/test",
            address="300 ELM ST",
            city="AUSTIN",
            state="TX",
            zip_code="73301",
            list_price=Decimal("300000.00"),
            status="for_sale",
            vendee_eligible=True,
            scraped_at=now,
            last_seen_at=now,
        )

    def test_list_all(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 3)

    def test_filter_by_state(self):
        resp = self.client.get(self.url + "?state=VA")
        data = resp.json()
        self.assertEqual(data["count"], 2)
        self.assertTrue(all(p["state"] == "VA" for p in data["results"]))

    def test_filter_by_zip(self):
        resp = self.client.get(self.url + "?zip=23220")
        data = resp.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["zip_code"], "23220")

    def test_filter_by_state_and_zip(self):
        resp = self.client.get(self.url + "?state=VA&zip=23505")
        data = resp.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["city"], "NORFOLK")

    def test_invalid_state(self):
        resp = self.client.get(self.url + "?state=ZZ")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid state code", resp.json()["error"])

    def test_invalid_zip_short(self):
        resp = self.client.get(self.url + "?zip=123")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("5 digits", resp.json()["error"])

    def test_invalid_zip_letters(self):
        resp = self.client.get(self.url + "?zip=abcde")
        self.assertEqual(resp.status_code, 400)

    def test_pagination(self):
        resp = self.client.get(self.url + "?page=1&page_size=2")
        data = resp.json()
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["total_pages"], 2)


class VrmPropertyScrapeAPITest(TestCase):
    """Tests for POST /api/v1/vrm-properties/scrape/."""

    def setUp(self):
        self.client = Client()
        self.url = "/api/v1/vrm-properties/scrape/"

    def test_missing_state(self):
        resp = self.client.post(self.url, {}, content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("required", resp.json()["error"])

    def test_invalid_state(self):
        resp = self.client.post(
            self.url, {"state": "ZZ"}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid state code", resp.json()["error"])


class VrmPropertiesUITest(TestCase):
    """Tests for /vrm-properties/ UI page."""

    def setUp(self):
        from django.contrib.auth.models import User
        from django.test import RequestFactory

        self.factory = RequestFactory()
        self.user = User.objects.create_user("testadmin", password="testpass")

    def _get(self, **params):
        from core.views import vrm_properties_list

        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"/vrm-properties/{f'?{query}' if query else ''}"
        request = self.factory.get(url)
        request.user = self.user
        return vrm_properties_list(request)

    def test_page_renders(self):
        resp = self._get()
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"VRM Properties", resp.content)

    def test_page_has_state_dropdown(self):
        resp = self._get()
        self.assertIn(b"All States", resp.content)
        self.assertIn(b"Virginia", resp.content)

    def test_page_has_zip_input(self):
        resp = self._get()
        self.assertIn(b"Zip Code", resp.content)

    def test_page_has_scrape_button(self):
        resp = self._get()
        self.assertIn(b"Scrape Selected State", resp.content)

    def test_filter_by_state(self):
        VrmProperty.objects.create(
            vrm_property_id=20001,
            vrm_listing_url="https://vrmproperties.com/Property-For-Sale/20001/test",
            address="100 MAIN ST",
            city="RICHMOND",
            state="VA",
            zip_code="23220",
            list_price=Decimal("200000.00"),
            status="for_sale",
            vendee_eligible=False,
            scraped_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        resp = self._get(state="VA")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"100 MAIN ST", resp.content)

    def test_filter_by_zip(self):
        VrmProperty.objects.create(
            vrm_property_id=20002,
            vrm_listing_url="https://vrmproperties.com/Property-For-Sale/20002/test",
            address="200 OAK AVE",
            city="NORFOLK",
            state="VA",
            zip_code="23505",
            list_price=Decimal("180000.00"),
            status="for_sale",
            vendee_eligible=False,
            scraped_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        resp = self._get(zip="23505")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"200 OAK AVE", resp.content)
