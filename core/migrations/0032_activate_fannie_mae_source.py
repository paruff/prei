"""Activate the Fannie Mae HomePath property source."""

from __future__ import annotations

from django.db import migrations


def activate_source(apps, schema_editor):  # type: ignore[no-untyped-def]
    PropertySource = apps.get_model("core", "PropertySource")
    PropertySource.objects.filter(source_type="fannie").update(is_active=True)


def deactivate_source(apps, schema_editor):  # type: ignore[no-untyped-def]
    PropertySource = apps.get_model("core", "PropertySource")
    PropertySource.objects.filter(source_type="fannie").update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0031_seed_property_sources"),
    ]

    operations = [
        migrations.RunPython(activate_source, deactivate_source),
    ]
