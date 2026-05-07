from decimal import Decimal, InvalidOperation

from django.shortcuts import render

from core.services.portfolio import aggregate_portfolio, compare_scenarios


def portfolio_dashboard(request):
    if not request.user.is_authenticated:
        return render(
            request,
            "portfolio_dashboard.html",
            {"error": "Please sign in to view your portfolio."},
            status=403,
        )

    agg = aggregate_portfolio(request.user)
    # Minimal trend placeholder; real implementation would compute series
    trend = [
        {"month": "Jan", "noi": float(agg["total_noi"]) / 12.0},
        {"month": "Feb", "noi": float(agg["total_noi"]) / 12.0},
        {"month": "Mar", "noi": float(agg["total_noi"]) / 12.0},
    ]

    scenario_results = None
    if request.method == "POST":
        scenarios = []
        for i in range(1, 4):
            label = (
                request.POST.get(f"scenario_{i}_label", "").strip() or f"Scenario {i}"
            )
            vacancy_raw = request.POST.get(f"scenario_{i}_vacancy", "").strip()
            interest_raw = request.POST.get(f"scenario_{i}_interest", "").strip()
            price_delta_raw = request.POST.get(f"scenario_{i}_price_delta", "").strip()

            # Only include this scenario if at least one numeric override was supplied
            if not any([vacancy_raw, interest_raw, price_delta_raw]):
                continue

            overrides: dict = {"label": label}
            if vacancy_raw:
                try:
                    # Form input is a percentage (e.g. "10") → convert to 0–1 rate
                    overrides["vacancy_rate"] = Decimal(str(vacancy_raw)) / Decimal(
                        "100"
                    )
                except InvalidOperation:
                    pass
            if interest_raw:
                try:
                    overrides["interest_rate"] = Decimal(str(interest_raw))
                except InvalidOperation:
                    pass
            if price_delta_raw:
                try:
                    overrides["purchase_price_delta_pct"] = Decimal(
                        str(price_delta_raw)
                    )
                except InvalidOperation:
                    pass

            scenarios.append(overrides)

        if scenarios:
            scenario_results = compare_scenarios(request.user, scenarios)

    return render(
        request,
        "portfolio_dashboard.html",
        {"agg": agg, "trend": trend, "scenario_results": scenario_results},
    )
