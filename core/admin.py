from django.contrib import admin

from .models import (
    Property,
    RentalIncome,
    OperatingExpense,
    Transaction,
    InvestmentAnalysis,
)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("address", "city", "state", "purchase_price", "units")
    search_fields = ("address", "city", "state", "zip_code")


@admin.register(RentalIncome)
class RentalIncomeAdmin(admin.ModelAdmin):
    list_display = ("property", "monthly_rent", "vacancy_rate", "effective_date")


@admin.register(OperatingExpense)
class OperatingExpenseAdmin(admin.ModelAdmin):
    list_display = ("property", "category", "amount", "frequency", "effective_date")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("property", "type", "amount", "date")


@admin.register(InvestmentAnalysis)
class InvestmentAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "property",
        "noi",
        "cap_rate",
        "cash_on_cash",
        "irr",
        "dscr",
        "updated_at",
    )
