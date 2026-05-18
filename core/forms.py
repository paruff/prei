from __future__ import annotations

from django import forms

from .models import OperatingExpense, Property, RentalIncome


class PropertyForm(forms.ModelForm):
    property_type = forms.CharField(required=False, max_length=64)
    square_footage = forms.IntegerField(required=False, min_value=0)
    num_units = forms.IntegerField(required=False, min_value=1, initial=1)
    year_built = forms.IntegerField(required=False, min_value=0)

    class Meta:
        model = Property
        fields = [
            "address",
            "city",
            "state",
            "zip_code",
            "purchase_price",
            "purchase_date",
            "property_type",
            "square_footage",
            "num_units",
            "year_built",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["square_footage"].initial = self.instance.sqft
            self.fields["num_units"].initial = self.instance.units

    def save(self, commit: bool = True) -> Property:
        instance = super().save(commit=False)
        instance.sqft = self.cleaned_data.get("square_footage")
        instance.units = self.cleaned_data.get("num_units") or 1
        if commit:
            instance.save()
        return instance


class RentalIncomeForm(forms.ModelForm):
    class Meta:
        model = RentalIncome
        fields = ["monthly_rent", "vacancy_rate", "effective_date"]


class OperatingExpenseForm(forms.ModelForm):
    class Meta:
        model = OperatingExpense
        fields = ["category", "amount", "frequency", "effective_date"]
