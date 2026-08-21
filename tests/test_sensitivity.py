"""Sensitivity analysis table tests for rent, vacancy, and rate scenarios."""

from decimal import Decimal

from core.services.underwriting import UnderwritingInput
from core.services.sensitivity import sensitivity_analysis_table

BASE = UnderwritingInput(
    purchase_price=Decimal("300000"),
    estimated_rent=Decimal("2500"),
    property_tax_annual=Decimal("3600"),
    insurance_annual=Decimal("1200"),
)


# ═════════════════════════════════════════════════════════════════════════════
#  BASIC FUNCTIONALITY
# ═════════════════════════════════════════════════════════════════════════════


class TestSensitivityAnalysisTableBasic:
    def test_returns_list(self) -> None:
        """Table should be a non-empty list of dicts."""
        rows = sensitivity_analysis_table(BASE)
        assert isinstance(rows, list)
        assert len(rows) > 0

    def test_rows_are_dicts(self) -> None:
        """Each row should be a dict with expected keys."""
        rows = sensitivity_analysis_table(BASE)
        assert all(isinstance(r, dict) for r in rows)

    def test_rows_have_expected_keys(self) -> None:
        """Each row should contain all expected keys."""
        rows = sensitivity_analysis_table(BASE)
        expected_keys = {
            "rent",
            "vacancy_rate",
            "cap_rate",
            "noi",
            "cap_rate_result",
            "cash_on_cash",
            "mao",
        }
        for row in rows:
            assert set(row.keys()) == expected_keys

    def test_rent_varies_across_multipliers(self) -> None:
        """Rent should vary across the default multipliers."""
        rows = sensitivity_analysis_table(BASE)
        rents = {row["rent"] for row in rows}
        # 5 multipliers × 5 vacancies × 6 caps = 150 rows
        assert len(rents) == 5

    def test_vacancy_varies_across_rates(self) -> None:
        """Vacancy rate should vary across the default rates."""
        rows = sensitivity_analysis_table(BASE)
        vacs = {row["vacancy_rate"] for row in rows}
        assert len(vacs) == 5

    def test_cap_rate_varies_across_scanners(self) -> None:
        """Cap rate scanner should vary across the default values."""
        rows = sensitivity_analysis_table(BASE)
        caps = {row["cap_rate"] for row in rows}
        assert len(caps) == 6


# ═════════════════════════════════════════════════════════════════════════════
#  SCENARIO-SPECIFIC ASSERTIONS
# ═════════════════════════════════════════════════════════════════════════════


class TestSensitivityScenarioRentIncrease:
    """Rent increase should improve all else-equal metrics."""

    def test_higher_rent_better_noi(self) -> None:
        """Higher rent → higher NOI (all else equal)."""
        rows = sensitivity_analysis_table(BASE)
        # Find rows with same vacancy and cap but different rents
        by_vac_cap: dict[tuple[Decimal, Decimal], list[dict]] = {}
        for row in rows:
            key = (row["vacancy_rate"], row["cap_rate"])
            by_vac_cap.setdefault(key, []).append(row)

        for key, group in by_vac_cap.items():
            # Within each (vacancy, cap) group, rents should be ordered
            # multipliers are [0.8, 0.9, 1.0, 1.1, 1.2], so NOI should increase
            NOIs = [row["noi"] for row in group]
            assert NOIs == sorted(NOIs), f"NOIs not sorted for {key}: {NOIs}"


class TestSensitivityScenarioVacancyIncrease:
    """Vacancy increase should worsen NOI all else equal."""

    def test_higher_vacancy_worse_noi(self) -> None:
        """Higher vacancy → lower NOI (all else equal)."""
        rows = sensitivity_analysis_table(BASE)
        by_rent_cap: dict[tuple[Decimal, Decimal], list[dict]] = {}
        for row in rows:
            key = (row["rent"], row["cap_rate"])
            by_rent_cap.setdefault(key, []).append(row)

        for key, group in by_rent_cap.items():
            NOIs = [row["noi"] for row in group]
            assert NOIs == sorted(NOIs, reverse=True), (
                f"NOIs not descending for rent={key[0]} cap={key[1]}: {NOIs}"
            )


class TestSensitivityScenarioCapRateIncrease:
    """Cap rate increase should lower MAO all else equal."""

    def test_higher_cap_rate_lower_mao(self) -> None:
        """Higher cap rate → lower MAO (all else equal)."""
        rows = sensitivity_analysis_table(BASE)
        by_rent_vac: dict[tuple[Decimal, Decimal], list[dict]] = {}
        for row in rows:
            key = (row["rent"], row["vacancy_rate"])
            by_rent_vac.setdefault(key, []).append(row)

        for key, group in by_rent_vac.items():
            maos = [row["mao"] for row in group]
            # Default caps are [0.05, 0.06, 0.07, 0.08, 0.09, 0.10] (ascending)
            # MAO = NOI / cap_rate, so MAO must be strictly decreasing
            for i in range(len(maos) - 1):
                assert maos[i] > maos[i + 1], (
                    f"MAO not strictly decreasing for rent={key[0]} "
                    f"vac={key[1]}: {maos}"
                )


# ════════════════════════════════════════════════════════════════════════════
#  CUSTOM PARAMETERS
# ════════════════════════════════════════════════════════════════════════════


class TestSensitivityCustomParams:
    def test_custom_rent_multipliers(self) -> None:
        """Custom rent multipliers should be used."""
        custom_multipliers = [Decimal("0.90"), Decimal("1.00"), Decimal("1.10")]
        rows = sensitivity_analysis_table(BASE, rent_multipliers=custom_multipliers)
        rents = {row["rent"] for row in rows}
        assert rents == {BASE.estimated_rent * m for m in custom_multipliers}

    def test_custom_vacancy_rates(self) -> None:
        """Custom vacancy rates should be used."""
        custom_vacancies = [Decimal("0.05"), Decimal("0.10")]
        rows = sensitivity_analysis_table(BASE, vacancy_rates=custom_vacancies)
        vacs = {row["vacancy_rate"] for row in rows}
        assert vacs == set(custom_vacancies)

    def test_custom_cap_rate_scanners(self) -> None:
        """Custom cap rate scanners should be used."""
        custom_caps = [Decimal("0.07"), Decimal("0.09")]
        rows = sensitivity_analysis_table(BASE, cap_rate_scanners=custom_caps)
        caps = {row["cap_rate"] for row in rows}
        assert caps == set(custom_caps)


# ════════════════════════════════════════════════════════════════════════════
#  INTEGRITY / EDGE CASES
# ════════════════════════════════════════════════════════════════════════════


class TestSensitivityIntegrity:
    def test_noi_always_decimal(self) -> None:
        """NOI should always be a Decimal."""
        rows = sensitivity_analysis_table(BASE)
        for row in rows:
            assert isinstance(row["noi"], Decimal)

    def test_mao_always_decimal(self) -> None:
        """MAO should always be a Decimal."""
        rows = sensitivity_analysis_table(BASE)
        for row in rows:
            assert isinstance(row["mao"], Decimal)

    def test_cash_on_cash_always_decimal(self) -> None:
        """Cash-on-Cash should always be a Decimal."""
        rows = sensitivity_analysis_table(BASE)
        for row in rows:
            assert isinstance(row["cash_on_cash"], Decimal)

    def test_no_duplicate_rows(self) -> None:
        """Should not have duplicate rows with identical parameter combos."""
        rows = sensitivity_analysis_table(BASE)
        seen: set[tuple] = set()
        for row in rows:
            key = (row["rent"], row["vacancy_rate"], row["cap_rate"])
            assert key not in seen, f"Duplicate row found: {key}"
            seen.add(key)
