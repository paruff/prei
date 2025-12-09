from django.contrib import admin

from .models import (
    ForeclosureProperty,
    InvestmentAnalysis,
    Listing,
    SavedSearch,
    OperatingExpense,
    Property,
    RentalIncome,
    Transaction,
    MarketSnapshot,
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


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "address",
        "city",
        "state",
        "price",
        "beds",
        "baths",
        "sq_ft",
        "source",
        "posted_at",
    )
    list_filter = ("source", "property_type", "state")
    search_fields = ("address", "city", "state", "zip_code", "url")


@admin.register(MarketSnapshot)
class MarketSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "area_type",
        "zip_code",
        "city",
        "state",
        "rent_index",
        "price_trend",
        "updated_at",
    )
    list_filter = ("area_type", "state")
    search_fields = ("zip_code", "city", "state")

@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "state", "zip_code", "min_price", "max_price", "created_at")
    search_fields = ("name", "state", "zip_code")


@admin.register(ForeclosureProperty)
class ForeclosurePropertyAdmin(admin.ModelAdmin):
    list_display = (
        "property_id",
        "street",
        "city",
        "state",
        "foreclosure_status",
        "auction_date",
        "opening_bid",
        "data_source",
    )
    list_filter = ("foreclosure_status", "property_type", "state", "data_source")
    search_fields = (
        "property_id",
        "street",
        "city",
        "state",
        "zip_code",
        "case_number",
    )
    date_hierarchy = "auction_date"
