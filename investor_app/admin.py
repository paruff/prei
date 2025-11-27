"""Admin configuration for investor_app."""

from django.contrib import admin

from .models import (
    InvestmentAnalysis,
    OperatingExpense,
    Property,
    RentalIncome,
)

admin.site.register(Property)
admin.site.register(RentalIncome)
admin.site.register(OperatingExpense)
admin.site.register(InvestmentAnalysis)
