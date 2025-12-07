from __future__ import annotations

from decimal import Decimal

from django.shortcuts import render

from .models import Property, InvestmentAnalysis, OperatingExpense, RentalIncome
from investor_app.finance.utils import compute_analysis_for_property


def dashboard(request):
    properties = Property.objects.all()[:20]
    analyses: list[InvestmentAnalysis] = []
    for p in properties:
        analysis = compute_analysis_for_property(p)
        analyses.append(analysis)
    return render(request, "dashboard.html", {"analyses": analyses})
