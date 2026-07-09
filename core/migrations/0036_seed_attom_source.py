"""Add ATTOM Data Solutions as a property source."""

from __future__ import annotations

from django.db import migrations

ATT = "attom"


def seed_attom(apps, schema_editor):  # type: ignore[no-untyped-def]
    PropertySource = apps.get_model("core", "PropertySource")
    PropertySource.objects.update_or_create(
        source_type=ATT,
        defaults={
            "source_type": ATT,
            "name": "ATTOM Preforeclosures",
            "description": "Pre-foreclosure notices (NOD, NTS, Lis Pendens) from ATTOM Data Solutions. Requires a paid API key (ATTOM_API_KEY). Covers property address, lender, trustee, sale date, and unpaid balance.",
            "website_url": "https://api.attomdata.com",
            "is_free": False,
            "is_active": True,
            "sort_order": 8,
        },
    )


def remove_attom(apps, schema_editor):  # type: ignore[no-untyped-def]
    PropertySource = apps.get_model("core", "PropertySource")
    PropertySource.objects.filter(source_type=ATT).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0035_add_usda_removed_status"),
    ]

    operations = [
        migrations.RunPython(seed_attom, remove_attom),
    ]
