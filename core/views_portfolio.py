from django.shortcuts import render

from core.services.portfolio import aggregate_portfolio


def portfolio_dashboard(request):
    if not request.user.is_authenticated:
        return render(request, "portfolio_dashboard.html", {"error": "Please sign in to view your portfolio."}, status=403)

    agg = aggregate_portfolio(request.user)
    # Minimal trend placeholder; real implementation would compute series
    trend = [
        {"month": "Jan", "noi": float(agg["total_noi"]) / 12.0},
        {"month": "Feb", "noi": float(agg["total_noi"]) / 12.0},
        {"month": "Mar", "noi": float(agg["total_noi"]) / 12.0},
    ]
    return render(request, "portfolio_dashboard.html", {"agg": agg, "trend": trend})
