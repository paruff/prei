from __future__ import annotations

from typing import cast

from django import forms

from .models import OperatingExpense, Property, RentalIncome, UserInvestmentTargets

MIN_REALISTIC_YEAR_BUILT = 1800


class PropertyForm(forms.ModelForm):
    """Form for creating and editing properties with all MVP data-entry fields."""

    property_type = forms.ChoiceField(
        choices=[("", "---------")] + Property.PROPERTY_TYPE_CHOICES,
        required=False,
        initial="SFR",
    )
    square_footage = forms.IntegerField(required=False, min_value=0)
    num_units = forms.IntegerField(required=False, min_value=1, initial=1)
    year_built = forms.IntegerField(required=False, min_value=MIN_REALISTIC_YEAR_BUILT)

    class Meta:
        model = Property
        fields = [
            # Location
            "address",
            "city",
            "state",
            "zip_code",
            # Property details
            "property_type",
            "bedrooms",
            "bathrooms",
            "square_footage",
            "num_units",
            "year_built",
            # Purchase
            "purchase_price",
            "purchase_date",
            # Income
            "monthly_rent_gross",
            "other_monthly_income",
            # Expenses
            "property_taxes_annual",
            "insurance_annual",
            "hoa_monthly",
            # Loan
            "down_payment_pct",
            "interest_rate",
            "loan_term_years",
            # Assumptions
            "vacancy_rate",
            "mgmt_fee_pct",
            "maintenance_monthly",
            "capex_monthly",
        ]
        widgets = {
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={"class": "form-control", "maxlength": "2"}),
            "zip_code": forms.TextInput(attrs={"class": "form-control"}),
            "purchase_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "purchase_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "bedrooms": forms.NumberInput(attrs={"class": "form-control"}),
            "bathrooms": forms.NumberInput(attrs={"class": "form-control", "step": "0.5"}),
            "monthly_rent_gross": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "other_monthly_income": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "property_taxes_annual": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "insurance_annual": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "hoa_monthly": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "down_payment_pct": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "interest_rate": forms.NumberInput(attrs={"class": "form-control", "step": "0.0001"}),
            "loan_term_years": forms.NumberInput(attrs={"class": "form-control"}),
            "vacancy_rate": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "mgmt_fee_pct": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "maintenance_monthly": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "capex_monthly": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["square_footage"].initial = self.instance.sqft
            self.fields["num_units"].initial = self.instance.units

    def save(self, commit: bool = True) -> Property:
        """Persist form values while mapping UX field names to model field names.

        Args:
            commit: Whether to immediately save the model instance.

        Returns:
            The updated property instance.
        """
        instance = cast(Property, super().save(commit=False))
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


class InvestmentTargetsForm(forms.ModelForm):
    """Form for editing a user's underwriting thresholds and assumptions."""

    class Meta:
        model = UserInvestmentTargets
        fields = [
            "min_coc_pct",
            "min_dscr",
            "max_grm",
            "require_one_pct_rule",
            "target_hold_years",
            "annual_rent_growth_assumption",
            "annual_appreciation_assumption",
            "marginal_tax_rate",
        ]
        widgets = {
            "min_coc_pct": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "min_dscr": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "max_grm": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.1"}
            ),
            "require_one_pct_rule": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "target_hold_years": forms.NumberInput(attrs={"class": "form-control"}),
            "annual_rent_growth_assumption": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "annual_appreciation_assumption": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "marginal_tax_rate": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }
