from __future__ import annotations
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

User = get_user_model()


def compute_net_migration(
    population: int | None,
    pop_growth_rate: Decimal | None,
) -> tuple[int | None, Decimal | None]:
    """Estimate net migration and net migration rate from population data.

    Formula:
      prior_pop = current_pop / (1 + pop_growth_rate)
      natural_increase = prior_pop * 0.005
      net_migration = current_pop - prior_pop - natural_increase
      net_migration_rate = net_migration / prior_pop
    """
    if population is not None and pop_growth_rate is not None and pop_growth_rate != 0:
        prior_pop = int(Decimal(population) / (Decimal("1") + pop_growth_rate))
        natural_increase = int(Decimal(prior_pop) * Decimal("0.005"))
        migration = population - prior_pop - natural_increase
        migration_rate = Decimal(migration) / Decimal(prior_pop)
        return migration, migration_rate.quantize(Decimal("0.0001"))
    return None, None


class Listing(models.Model):
    """Normalized real estate listing ingested from external sources.

    Fields capture essential attributes for filtering and scoring in Phase 1.
    """

    SOURCE_CHOICES = (
        ("dummy", "Dummy"),
        ("external", "External"),
    )

    source = models.CharField(max_length=64, choices=SOURCE_CHOICES)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=128, blank=True, default="")
    state = models.CharField(max_length=64, blank=True, default="")
    zip_code = models.CharField(max_length=16, blank=True, default="")
    price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    beds = models.PositiveIntegerField(default=0)
    baths = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal("0"))
    sq_ft = models.PositiveIntegerField(default=0)
    property_type = models.CharField(max_length=64, blank=True, default="")
    url = models.URLField(unique=True)
    posted_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-posted_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.address} ({self.city}, {self.state}) - ${self.price}"


class MarketSnapshot(models.Model):
    """Normalized market/area metrics for intelligence layer.

    Represents aggregated signals for a geographic area (e.g., ZIP or city/state).
    """

    area_type = models.CharField(max_length=16, default="zip")  # zip or city
    zip_code = models.CharField(max_length=16, blank=True, default="")
    city = models.CharField(max_length=128, blank=True, default="")
    state = models.CharField(max_length=64, blank=True, default="")

    # --- Phase 0: Census & BLS market indicators ---
    msa_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Metropolitan Statistical Area name",
    )
    population = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total population for ZIP/area",
    )
    population_growth_pct_5yr = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="5-year population growth as fraction (e.g. 0.0234 = 2.34%)",
    )
    unemployment_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Unemployment rate as fraction (e.g. 0.045 = 4.5%)",
    )
    median_household_income = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Median household income in dollars",
    )
    fetched_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this data was fetched from Census/BLS APIs",
    )

    # --- Existing metrics ---
    rent_index = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    price_trend = models.DecimalField(
        max_digits=6, decimal_places=4, default=Decimal("0")
    )  # % change
    crime_score = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("0")
    )  # lower better
    school_rating = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("0")
    )
    price_to_rent_ratio = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    population_growth_rate = models.DecimalField(
        max_digits=7, decimal_places=4, null=True, blank=True
    )
    employment_diversity_score = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    landlord_friendliness_score = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    rent_growth_rate = models.DecimalField(
        max_digits=7, decimal_places=4, null=True, blank=True
    )
    market_score = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )

    updated_at = models.DateTimeField(auto_now=True)
    data_source = models.CharField(
        max_length=64,
        blank=True,
        default="dummy",
        help_text="Adapter source for this snapshot (e.g. 'rentcast', 'dummy', 'mixed')",
    )

    class Meta:
        ordering = ["-price_trend", "-rent_index"]

    def __str__(self) -> str:
        label = self.zip_code or f"{self.city}, {self.state}".strip(", ")
        return (
            f"MarketSnapshot {label} (trend={self.price_trend}, rent={self.rent_index})"
        )


class SavedSearch(models.Model):
    """Persisted search filters for listings, per user."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="saved_searches"
    )
    name = models.CharField(max_length=128)
    query = models.CharField(max_length=255, blank=True, default="")
    zip_code = models.CharField(max_length=16, blank=True, default="")
    state = models.CharField(max_length=64, blank=True, default="")
    min_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    max_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"SavedSearch {self.name} ({self.state} {self.zip_code})"


class GrowthArea(models.Model):
    """Economic growth area data for real estate investment analysis."""

    state = models.CharField(max_length=2, db_index=True)
    city_name = models.CharField(max_length=255)
    metro_area = models.CharField(max_length=255, blank=True)
    population_growth_rate = models.DecimalField(max_digits=6, decimal_places=2)
    employment_growth_rate = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    median_income_growth = models.DecimalField(max_digits=6, decimal_places=2)
    housing_demand_index = models.IntegerField()
    supply_constraint_index = models.IntegerField(default=50, null=True, blank=True)
    school_score = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Average school rating (0-10) from GreatSchools API",
    )
    rent_growth_rate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Year-over-year 2BR FMR growth rate from HUD (populated by "
            "populate_growth_areas via FMR adapter).  Null when HUD_API_KEY "
            "is missing or entity ID lookup fails."
        ),
    )
    net_migration = models.IntegerField(
        null=True,
        blank=True,
        help_text="Estimated net migration (population change - natural increase)",
    )
    net_migration_rate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Net migration as fraction of prior population",
    )
    county_fips = models.CharField(
        max_length=5,
        blank=True,
        default="",
        help_text=(
            "5-character county FIPS code for QCEW employment lookup "
            "(e.g. '48113' for Dallas County TX)"
        ),
    )
    fmr_2br = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "HUD FY2026 2BR Fair Market Rent (40th pct rent floor, not market rent)"
        ),
    )
    fmr_year = models.IntegerField(
        null=True,
        blank=True,
        help_text="Fiscal year of the FMR data (e.g. 2026)",
    )
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    data_timestamp = models.DateTimeField()
    population = models.IntegerField(
        null=True, blank=True, help_text="Latest population from Census ACS"
    )
    composite_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Precomputed weighted growth score (computed on save)",
    )
    landlord_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        default=None,
        help_text="State landlord-friendliness score (0=tenant-friendly, 10=landlord-friendly)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["state", "city_name"], name="unique_state_city"
            ),
        ]
        ordering = ["-data_timestamp"]

    def __str__(self) -> str:  # noqa: D401
        return f"{self.city_name}, {self.state}"

    def composite_score_display(self) -> Decimal | None:
        """Return precomputed composite score, or compute on the fly if not stored."""
        if self.composite_score is not None:
            return self.composite_score
        return self._compute_composite_score()

    def _compute_composite_score(self) -> Decimal | None:
        """Calculate composite growth score based on weighted metrics.

        Returns None if none of the weighted factors are available (all are None/zero).
        Missing factors are treated as 0 so a partial score is still computable.

        Weights (GACS v2, confirmed 2026-07-10):
          - Employment growth rate:  0.30  (county-level QCEW preferred, FRED fallback)
          - Population growth rate:  0.15  (place-level, Census ACS)
          - Median income growth:    0.15  (place-level, Census ACS)
          - School quality score:    0.10  (place-level, GreatSchools API)
          - Rent growth (FMR YoY):   0.15  (county-level HUD FMR year-over-year)
          - Supply constraint index: 0.10  (place-level, Census ACS housing-unit growth)
          - Net migration proxy:     0.05  (estimated from ACS pop growth vs natural increase)
        """
        emp_weight = Decimal("0.30")
        pop_weight = Decimal("0.15")
        income_weight = Decimal("0.15")
        school_weight = Decimal("0.10")
        rent_weight = Decimal("0.15")
        supply_weight = Decimal("0.10")
        migration_weight = Decimal("0.05")

        emp_rate = self.employment_growth_rate or Decimal("0")
        pop_rate = self.population_growth_rate or Decimal("0")
        income_rate = self.median_income_growth or Decimal("0")
        rent_rate = self.rent_growth_rate or Decimal("0")
        supply_idx = (Decimal(self.supply_constraint_index or 0)) / Decimal("100")
        school_score_val = (
            (self.school_score / Decimal("10")) if self.school_score else Decimal("0")
        )
        migration_rate = (
            (self.net_migration_rate / Decimal("100"))
            if self.net_migration_rate
            else Decimal("0")
        )

        score = (
            emp_rate * emp_weight
            + pop_rate * pop_weight
            + income_rate * income_weight
            + school_score_val * school_weight
            + rent_rate * rent_weight
            + supply_idx * supply_weight
            + migration_rate * migration_weight
        )
        return score

    @property
    def data_confidence(self) -> int:
        """Confidence score 0-100 based on how many data points are real vs defaults.

        Each of the 7 GACS components is scored:
        - real value from API → ~14 points
        - employment: QCEW county-level = 17, FRED state-level = 8
        - rent growth when FMR source available = 14
        """
        c = 0
        # Employment: QCEW (county_fips set) = 17 pts, FRED fallback = 8 pts
        if self.employment_growth_rate is not None:
            c += 17 if self.county_fips else 8
        c += 14  # population_growth_rate: required
        c += 14  # median_income_growth: required
        if self.school_score is not None:
            c += 14
        if self.rent_growth_rate is not None:
            c += 14
        if (
            self.supply_constraint_index is not None
            and self.supply_constraint_index != 50
        ):
            c += 14
        if self.net_migration_rate is not None:
            c += 14
        return min(c, 100)

    @property
    def net_migration_proxy(self) -> int | None:
        """Estimated net migration using population growth as proxy.

        True migration requires births/deaths data (CDC Vital Statistics).
        This estimates it as: population_change - expected_natural_increase.
        Natural increase is approximated as 0.5% of prior population.
        Returns None if population data is unavailable.
        """
        from decimal import Decimal

        pop = self.population
        prior_pop = None
        # We can reverse-engineer prior pop from current pop and growth rate
        pop_growth = self.population_growth_rate
        if pop is not None and pop_growth is not None and pop_growth != 0:
            prior_pop = int(Decimal(pop) / (Decimal("1") + pop_growth))
            natural_increase = int(Decimal(prior_pop) * Decimal("0.005"))
            estimated_migration = pop - prior_pop - natural_increase
            return estimated_migration
        return None

    def save(self, *args, **kwargs):
        """Precompute composite_score on save."""
        self.composite_score = self._compute_composite_score()
        super().save(*args, **kwargs)
