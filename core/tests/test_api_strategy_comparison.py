"""Integration tests for strategy comparison API."""

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
def test_compare_flip_vs_rental(client):
    """Test comparing flip and rental strategies."""
    url = reverse("api:strategy-comparison")

    payload = {
        "propertyDetails": {
            "purchasePrice": 350000,
            "propertyType": "single-family",
            "squareFeet": 1850,
            "yearBuilt": 1995,
            "location": {
                "address": "123 Main St, Miami, FL 33139",
                "state": "FL",
                "zip": "33139",
            },
        },
        "financing": {
            "downPayment": 70000,
            "loanAmount": 280000,
            "interestRate": 7.5,
            "loanTermYears": 30,
            "closingCosts": 8500,
        },
        "operatingExpenses": {
            "propertyTaxRate": 2.1,
            "insuranceAnnual": 1800,
            "hoaMonthly": 0,
            "utilitiesMonthly": 200,
            "maintenanceAnnualPercent": 1.0,
            "propertyManagementPercent": 10,
            "vacancyRatePercent": 8,
        },
        "strategies": ["flip", "rental"],
        "assumptions": {
            "flip": {
                "renovationCosts": 50000,
                "holdingPeriodMonths": 6,
                "expectedSalePrice": 475000,
                "sellingCosts": 28500,
            },
            "rental": {
                "monthlyRent": 2500,
                "holdingPeriodYears": 5,
                "appreciationRate": 3.0,
            },
        },
    }

    response = client.post(url, payload, content_type="application/json")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify structure
    assert "property" in data
    assert "strategies" in data
    assert "recommendation" in data

    # Verify strategies are present
    assert "flip" in data["strategies"]
    assert "rental" in data["strategies"]

    # Verify flip strategy results
    flip = data["strategies"]["flip"]
    assert "totalInvestment" in flip
    assert "holdingCosts" in flip
    assert "renovationCosts" in flip
    assert "saleProceeds" in flip
    assert "netProfit" in flip
    assert "roi" in flip
    assert "annualizedReturn" in flip

    # Verify rental strategy results
    rental = data["strategies"]["rental"]
    assert "totalInvestment" in rental
    assert "year1CashFlow" in rental
    assert "roi" in rental
    assert "annualizedReturn" in rental

    # Verify recommendation
    recommendation = data["recommendation"]
    assert "bestStrategy" in recommendation
    assert "reasoning" in recommendation
    assert "riskFactors" in recommendation
    assert recommendation["bestStrategy"] in ["flip", "rental"]


@pytest.mark.django_db
def test_compare_all_strategies(client):
    """Test comparing all three strategies."""
    url = reverse("api:strategy-comparison")

    payload = {
        "propertyDetails": {
            "purchasePrice": 300000,
            "propertyType": "condo",
            "squareFeet": 1200,
            "yearBuilt": 2010,
            "location": {
                "address": "456 Beach Blvd, Miami, FL 33139",
                "state": "FL",
                "zip": "33139",
            },
        },
        "financing": {
            "downPayment": 60000,
            "loanAmount": 240000,
            "interestRate": 6.5,
            "loanTermYears": 30,
            "closingCosts": 5000,
        },
        "operatingExpenses": {
            "propertyTaxRate": 2.1,
            "insuranceAnnual": 1200,
            "hoaMonthly": 300,
            "utilitiesMonthly": 150,
            "maintenanceAnnualPercent": 0.5,
            "propertyManagementPercent": 10,
            "vacancyRatePercent": 8,
        },
        "strategies": ["flip", "rental", "vacation_rental"],
        "assumptions": {
            "flip": {
                "renovationCosts": 30000,
                "holdingPeriodMonths": 4,
                "expectedSalePrice": 380000,
                "sellingCosts": 22800,
            },
            "rental": {
                "monthlyRent": 2000,
                "holdingPeriodYears": 5,
                "appreciationRate": 3.0,
            },
            "vacation_rental": {
                "avgNightlyRate": 200,
                "avgOccupancyRate": 65,
                "cleaningFeePerStay": 150,
            },
        },
    }

    response = client.post(url, payload, content_type="application/json")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify all three strategies are present
    assert "flip" in data["strategies"]
    assert "rental" in data["strategies"]
    assert "vacation_rental" in data["strategies"]

    # Verify vacation rental specific fields
    vr = data["strategies"]["vacation_rental"]
    assert "avgMonthlyIncome" in vr
    assert "avgMonthlyExpenses" in vr
    assert "cocReturn" in vr
    assert "seasonalityImpact" in vr


@pytest.mark.django_db
def test_compare_strategies_missing_assumptions(client):
    """Test validation when assumptions are missing for a selected strategy."""
    url = reverse("api:strategy-comparison")

    payload = {
        "propertyDetails": {
            "purchasePrice": 300000,
            "propertyType": "single-family",
            "location": {"address": "123 Main St", "state": "FL", "zip": "33139"},
        },
        "financing": {
            "downPayment": 60000,
            "loanAmount": 240000,
            "interestRate": 6.5,
            "loanTermYears": 30,
        },
        "operatingExpenses": {
            "propertyTaxRate": 2.0,
            "hoaMonthly": 0,
            "utilitiesMonthly": 150,
            "maintenanceAnnualPercent": 1.0,
            "propertyManagementPercent": 10,
            "vacancyRatePercent": 8,
        },
        "strategies": ["flip", "rental"],
        "assumptions": {
            # Missing flip assumptions
            "rental": {
                "monthlyRent": 2000,
                "holdingPeriodYears": 5,
            },
        },
    }

    response = client.post(url, payload, content_type="application/json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_compare_strategies_single_strategy(client):
    """Test that single strategy comparison works."""
    url = reverse("api:strategy-comparison")

    payload = {
        "propertyDetails": {
            "purchasePrice": 200000,
            "propertyType": "multi-family",
            "squareFeet": 2000,
            "yearBuilt": 2000,
            "location": {
                "address": "789 Oak St, Cleveland, OH 44101",
                "state": "OH",
                "zip": "44101",
            },
        },
        "financing": {
            "downPayment": 50000,
            "loanAmount": 150000,
            "interestRate": 5.5,
            "loanTermYears": 30,
            "closingCosts": 3000,
        },
        "operatingExpenses": {
            "propertyTaxRate": 2.0,
            "insuranceAnnual": 1500,
            "hoaMonthly": 0,
            "utilitiesMonthly": 300,
            "maintenanceAnnualPercent": 1.5,
            "propertyManagementPercent": 8,
            "vacancyRatePercent": 10,
        },
        "strategies": ["rental"],
        "assumptions": {
            "rental": {
                "monthlyRent": 2500,
                "holdingPeriodYears": 5,
                "appreciationRate": 3.0,
            },
        },
    }

    response = client.post(url, payload, content_type="application/json")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Only rental strategy should be present
    assert "rental" in data["strategies"]
    assert "flip" not in data["strategies"]
    assert "vacation_rental" not in data["strategies"]

    # Recommendation should be rental (only option)
    assert data["recommendation"]["bestStrategy"] == "rental"
