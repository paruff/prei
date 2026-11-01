import logging

from django.db import migrations

logger = logging.getLogger(__name__)


def month_to_first(apps, schema_editor):
    """Move mid-month rows to the 1st; the newest row of a month wins a collision."""
    MonthlyActuals = apps.get_model("core", "MonthlyActuals")
    keep: dict = {}
    for row in MonthlyActuals.objects.order_by("pk"):
        key = (row.prop_id, row.month.replace(day=1))
        if key in keep:
            old = keep[key]  # older row of the same month
            logger.warning(
                "monthly actuals: dropping pk=%s prop=%s month=%s rent=%s "
                "(superseded by pk=%s)",
                old.pk,
                old.prop_id,
                old.month,
                old.actual_rent_collected,
                row.pk,
            )
            old.delete()
        keep[key] = row
    for (_, first), row in keep.items():
        if row.month != first:
            logger.warning(
                "monthly actuals: pk=%s prop=%s month %s -> %s",
                row.pk,
                row.prop_id,
                row.month,
                first,
            )
            row.month = first
            row.save(update_fields=["month"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0053_pipelineproperty_underwriting_rates"),
    ]

    operations = [
        migrations.RunPython(month_to_first, migrations.RunPython.noop),
    ]
