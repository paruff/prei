from django.db import migrations


def month_to_first(apps, schema_editor):
    """Move mid-month rows to the 1st; the newest row of a month wins a collision."""
    MonthlyActuals = apps.get_model("core", "MonthlyActuals")
    keep: dict = {}
    for row in MonthlyActuals.objects.order_by("pk"):
        key = (row.prop_id, row.month.replace(day=1))
        if key in keep:
            keep[key].delete()  # older row of the same month
        keep[key] = row
    for (_, first), row in keep.items():
        if row.month != first:
            row.month = first
            row.save(update_fields=["month"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0053_pipelineproperty_underwriting_rates"),
    ]

    operations = [
        migrations.RunPython(month_to_first, migrations.RunPython.noop),
    ]
