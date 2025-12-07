from __future__ import annotations

# removed unused Decimal import
from django.shortcuts import render

# keep only the models that are actually used
from .models import Property, InvestmentAnalysis
from investor_app.finance.utils import compute_analysis_for_property


def dashboard(request):
    properties = Property.objects.all()[:20]
    analyses: list[InvestmentAnalysis] = []
    for p in properties:
        analysis = compute_analysis_for_property(p)
        analyses.append(analysis)
    return render(request, "dashboard.html", {"analyses": analyses})
