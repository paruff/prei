"""Seed the initial property sources for the discovery page."""

from __future__ import annotations

from django.db import migrations

# PipelineProperty.SourceType constants (copied to avoid import dependency)
VRM = "vrm"
FORECLOSURE = "foreclosure"
LISTING = "listing"
MANUAL = "manual"
HUD = "hud"
USDA = "usda"
FANNIE = "fannie"
FREDDIE = "freddie"
COUNTY = "county"
BANK_REO = "bank_reo"


def seed_sources(apps, schema_editor):  # type: ignore[no-untyped-def]
    PropertySource = apps.get_model("core", "PropertySource")

    sources = [
        {
            "source_type": FANNIE,
            "name": "Fannie Mae HomePath",
            "description": "REO listings from Fannie Mae — public foreclosure properties available for purchase. Free to browse, no API key needed.",
            "website_url": "https://www.homepath.com",
            "is_free": True,
            "is_active": False,
            "sort_order": 1,
        },
        {
            "source_type": HUD,
            "name": "HUD Homestore",
            "description": "Government-owned foreclosure properties from HUD. Primarily FHA-insured single-family homes. Free to browse.",
            "website_url": "https://www.hudhomestore.com",
            "is_free": True,
            "is_active": False,
            "sort_order": 2,
        },
        {
            "source_type": USDA,
            "name": "USDA Foreclosures",
            "description": "Rural foreclosure properties from USDA loans. Single-family homes in eligible rural areas. Free to browse.",
            "website_url": "https://www.sc.egov.usda.gov",
            "is_free": True,
            "is_active": False,
            "sort_order": 3,
        },
        {
            "source_type": COUNTY,
            "name": "County Foreclosure Notices",
            "description": "Public foreclosure notices from county registers — Notice of Default, Trustee Sale, Sheriff Sale, and auction calendars. Available via county websites, RSS feeds, JSON APIs, or CSV downloads. Free.",
            "website_url": "",
            "is_free": True,
            "is_active": False,
            "sort_order": 4,
        },
        {
            "source_type": VRM,
            "name": "VRM Foreclosures (Active)",
            "description": "Foreclosure properties from VRM (Vendor Risk Management) — our active scraper. Properties are already available in the Foreclosures view.",
            "website_url": "",
            "is_free": True,
            "is_active": True,
            "sort_order": 5,
        },
        {
            "source_type": FREDDIE,
            "name": "Freddie Mac HomeSteps",
            "description": "REO listings from Freddie Mac. Public foreclosure properties. Free to browse.",
            "website_url": "https://www.homesteps.com",
            "is_free": True,
            "is_active": False,
            "sort_order": 6,
        },
        {
            "source_type": BANK_REO,
            "name": "Bank REO Properties",
            "description": "Real Estate Owned properties from major bank inventories (Chase, Wells Fargo, BofA). Often listed on publicly accessible bank REO portals. Free to browse.",
            "website_url": "",
            "is_free": True,
            "is_active": False,
            "sort_order": 7,
        },
        {
            "source_type": LISTING,
            "name": "MLS Listings",
            "description": "Multiple Listing Service properties. Requires realtor access or paid syndication feeds (e.g., ListHub, IDX). For-fee service.",
            "website_url": "",
            "is_free": False,
            "is_active": False,
            "sort_order": 10,
        },
    ]

    for src in sources:
        PropertySource.objects.update_or_create(
            source_type=src["source_type"],
            defaults=src,
        )


def remove_sources(apps, schema_editor):  # type: ignore[no-untyped-def]
    PropertySource = apps.get_model("core", "PropertySource")
    PropertySource.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0030_property_discovery"),
    ]

    operations = [
        migrations.RunPython(seed_sources, remove_sources),
    ]
