from __future__ import annotations

from typing import cast

from django import forms

from .models import OperatingExpense, Property, RentalIncome, UserInvestmentTargets

MIN_REALISTIC_YEAR_BUILT = 1800


class StyledNumberInput(forms.NumberInput):
    """NumberInput that auto-applies ``form-input num`` CSS class."""

    def __init__(self, *args, **kwargs):  # noqa: D401
        super().__init__(*args, **kwargs)
        self.attrs.setdefault("class", "form-input num")


class StyledTextInput(forms.TextInput):
    """TextInput that auto-applies ``form-input`` CSS class."""

    def __init__(self, *args, **kwargs):  # noqa: D401
        super().__init__(*args, **kwargs)
        self.attrs.setdefault("class", "form-input")


class StyledSelect(forms.Select):
    """Select that auto-applies ``form-input`` CSS class."""

    def __init__(self, *args, **kwargs):  # noqa: D401
        super().__init__(*args, **kwargs)
        self.attrs.setdefault("class", "form-input")


class PropertyForm(forms.ModelForm):
    """Form for creating and editing properties with all MVP data-entry fields."""

    property_type = forms.ChoiceField(
        choices=[("", "---------")] + Property.PROPERTY_TYPE_CHOICES,
        required=False,
        initial="SFR",
        widget=StyledSelect(),
    )
    square_footage = forms.IntegerField(
        required=False,
        min_value=0,
        widget=StyledNumberInput(attrs={"step": "100", "min": "0"}),
    )
    num_units = forms.IntegerField(
        required=False,
        min_value=1,
        initial=1,
        widget=StyledNumberInput(attrs={"step": "1", "min": "1"}),
    )
    year_built = forms.IntegerField(
        required=False,
        min_value=MIN_REALISTIC_YEAR_BUILT,
        widget=StyledNumberInput(attrs={"step": "1", "min": "1800", "max": "2030"}),
    )

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
            "address": StyledTextInput(),
            "city": StyledTextInput(),
            "state": StyledTextInput(attrs={"maxlength": "2"}),
            "zip_code": StyledTextInput(),
            "property_type": StyledSelect(),
            "purchase_price": StyledNumberInput(attrs={"step": "1000", "min": "0"}),
            "purchase_date": forms.DateInput(
                attrs={"type": "date", "class": "form-input"}
            ),
            "bedrooms": StyledNumberInput(attrs={"step": "1", "min": "0"}),
            "bathrooms": StyledNumberInput(attrs={"step": "0.5"}),
            "year_built": StyledNumberInput(
                attrs={"step": "1", "min": "1800", "max": "2030"}
            ),
            "monthly_rent_gross": StyledNumberInput(attrs={"step": "50", "min": "0"}),
            "other_monthly_income": StyledNumberInput(attrs={"step": "10", "min": "0"}),
            "property_taxes_annual": StyledNumberInput(
                attrs={"step": "100", "min": "0"}
            ),
            "insurance_annual": StyledNumberInput(attrs={"step": "100", "min": "0"}),
            "hoa_monthly": StyledNumberInput(attrs={"step": "10", "min": "0"}),
            "maintenance_monthly": StyledNumberInput(attrs={"step": "10", "min": "0"}),
            "capex_monthly": StyledNumberInput(attrs={"step": "10", "min": "0"}),
            "down_payment_pct": StyledNumberInput(
                attrs={"step": "1", "min": "0", "max": "100"}
            ),
            "interest_rate": StyledNumberInput(
                attrs={"step": "0.125", "min": "0", "max": "30"}
            ),
            "loan_term_years": StyledNumberInput(
                attrs={"step": "1", "min": "1", "max": "40"}
            ),
            "vacancy_rate": StyledNumberInput(
                attrs={"step": "1", "min": "0", "max": "100"}
            ),
            "mgmt_fee_pct": StyledNumberInput(
                attrs={"step": "1", "min": "0", "max": "50"}
            ),
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
