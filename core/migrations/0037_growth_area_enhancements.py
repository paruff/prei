"""Add school_score, rent_growth_rate, net_migration to GrowthArea."""

from __future__ import annotations


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0036_seed_attom_source"),
    ]

    operations = [
        migrations.AddField(
            model_name="growtharea",
            name="school_score",
            field=models.DecimalField(
                max_digits=4,
                decimal_places=1,
                null=True,
                blank=True,
                help_text="Average school rating (0-10) from GreatSchools API",
            ),
        ),
        migrations.AddField(
            model_name="growtharea",
            name="rent_growth_rate",
            field=models.DecimalField(
                max_digits=6,
                decimal_places=2,
                null=True,
                blank=True,
                help_text="5-year gross rent growth rate from Census ACS",
            ),
        ),
        migrations.AddField(
            model_name="growtharea",
            name="net_migration",
            field=models.IntegerField(
                null=True,
                blank=True,
                help_text="Estimated net migration (population change - natural increase)",
            ),
        ),
        migrations.AddField(
            model_name="growtharea",
            name="net_migration_rate",
            field=models.DecimalField(
                max_digits=6,
                decimal_places=2,
                null=True,
                blank=True,
                help_text="Net migration as fraction of prior population",
            ),
        ),
    ]
