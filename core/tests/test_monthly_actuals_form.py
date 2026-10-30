from core.views_portfolio import MonthlyActualsForm


def _data(month: str) -> dict[str, str]:
    return {
        "month": month,
        "actual_rent_collected": "1500.00",
        "actual_vacancy_days": "0",
        "actual_expenses": "300.00",
        "actual_maintenance": "50.00",
    }


def test_month_input_value_is_accepted():
    form = MonthlyActualsForm(_data("2026-10"))
    assert form.is_valid(), form.errors
    assert form.cleaned_data["month"].isoformat() == "2026-10-01"


def test_full_date_still_accepted():
    assert MonthlyActualsForm(_data("2026-10-01")).is_valid()
