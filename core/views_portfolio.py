from django import forms
from django.shortcuts import redirect, render

from core.models import MonthlyActuals, Property
from core.services.portfolio import (
    aggregate_portfolio,
    compute_portfolio_performance,
    monthly_income_series,
    portfolio_trend_summary,
)


class MonthlyActualsForm(forms.ModelForm):
    """Form for entering monthly actuals."""

    class Meta:
        model = MonthlyActuals
        fields = [
            "month",
            "actual_rent_collected",
            "actual_vacancy_days",
            "actual_expenses",
            "actual_maintenance",
            "notes",
        ]
        widgets = {
            "month": forms.DateInput(attrs={"type": "month", "class": "form-control"}),
            "actual_rent_collected": forms.NumberInput(
                attrs={"step": "0.01", "class": "form-control"}
            ),
            "actual_vacancy_days": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "max": "31"}
            ),
            "actual_expenses": forms.NumberInput(
                attrs={"step": "0.01", "class": "form-control"}
            ),
            "actual_maintenance": forms.NumberInput(
                attrs={"step": "0.01", "class": "form-control"}
            ),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


def portfolio_dashboard(request):
    if not request.user.is_authenticated:
        return render(
            request,
            "portfolio_dashboard.html",
            {"error": "Please sign in to view your portfolio."},
            status=403,
        )

    agg = aggregate_portfolio(request.user)
    monthly_series = monthly_income_series(request.user)
    trend_summary = portfolio_trend_summary(request.user)

    # Compute performance metrics
    performance = compute_portfolio_performance(request.user)

    return render(
        request,
        "portfolio.html",
        {
            "agg": agg,
            "monthly_series": monthly_series,
            "trend_summary": trend_summary,
            **performance,
        },
    )


def portfolio_actuals_add(request):
    """Add monthly actuals for a property."""
    if not request.user.is_authenticated:
        return redirect("login")

    if request.method != "POST":
        return redirect("portfolio_dashboard")

    property_id = request.POST.get("property_id")
    try:
        property_obj = Property.objects.get(pk=property_id, user=request.user)
    except Property.DoesNotExist:
        return redirect("portfolio_dashboard")

    form = MonthlyActualsForm(request.POST)
    if form.is_valid():
        actuals = form.save(commit=False)
        actuals.prop = property_obj
        actuals.save()

    return redirect("portfolio_dashboard")
