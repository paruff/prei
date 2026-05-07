from django.shortcuts import render

from core.services.portfolio import (
    aggregate_portfolio,
    monthly_income_series,
    portfolio_trend_summary,
)


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
    return render(
        request,
        "portfolio_dashboard.html",
        {
            "agg": agg,
            "monthly_series": monthly_series,
            "trend_summary": trend_summary,
        },
    )
