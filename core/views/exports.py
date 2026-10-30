from __future__ import annotations

import logging
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import cast

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpResponse,
)
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify
from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

from core.models import (
    Property,
    Transaction,
)


logger = logging.getLogger(__name__)
FinancingValue = str | int | float | Decimal | None


def _get_financing_value(
    data: Mapping[str, FinancingValue | None], *keys: str
) -> FinancingValue:
    """Return the first non-None value for any provided key in metadata.

    This handles mixed snake_case/camelCase key formats across existing
    financing metadata payloads.
    """
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return None


def _format_financing_value(
    value: FinancingValue, prefix: str = "", suffix: str = ""
) -> str:
    if value is None:
        return "N/A"
    try:
        number = Decimal(str(value))
        return f"{prefix}{number:,.2f}{suffix}"
    except InvalidOperation, TypeError, ValueError:
        return f"{prefix}{value}{suffix}"


def _generate_pdf(html: str) -> bytes:
    """Generate a PDF from HTML content using Playwright.

    Uses headless Chromium (already a project dependency) to render
    the HTML template and produce a PDF.  This replaces the prior
    xhtml2pdf approach which was incompatible with reportlab>=5.
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            pdf_bytes: bytes = page.pdf(format="A4", print_background=True)
            return pdf_bytes
        finally:
            browser.close()


@login_required
def export_pdf(request, pk: int) -> HttpResponse:
    """Render and return a one-page deal summary PDF for an owned property.

    Args:
        request: Authenticated Django request.
        pk: Property primary key.

    Returns:
        HttpResponse: PDF attachment response.

    Raises:
        Http404: If the property is missing or does not belong to the user.
    """
    property_obj = get_object_or_404(
        Property.objects.select_related("analysis").prefetch_related(
            "rental_incomes", "operating_expenses", "transactions"
        ),
        pk=pk,
        user=request.user,
    )
    analysis = getattr(property_obj, "analysis", None)
    rental_income = property_obj.rental_incomes.order_by(
        "-effective_date", "-id"
    ).first()
    default_vacancy_rate = cast(
        Decimal, settings.FINANCE_DEFAULTS.get("vacancy_rate", Decimal("0.05"))
    )
    vacancy_rate: Decimal = (
        rental_income.vacancy_rate
        if rental_income is not None
        else default_vacancy_rate
    )
    effective_gross_income = (
        rental_income.effective_gross_income()
        if rental_income is not None
        else Decimal("0")
    )

    loan_transaction = (
        property_obj.transactions.filter(type=Transaction.Type.LOAN)
        .order_by("-date", "-id")
        .first()
    )
    financing = None
    if loan_transaction:
        metadata = cast(dict[str, FinancingValue | None], loan_transaction.metadata)
        down_payment = _get_financing_value(metadata, "downPayment", "down_payment")
        interest_rate = _get_financing_value(metadata, "interestRate", "interest_rate")
        term_years = _get_financing_value(
            metadata, "loanTermYears", "loan_term_years", "term_years"
        )
        monthly_payment = _get_financing_value(
            metadata, "monthlyPayment", "monthly_payment"
        )
        financing = {
            "down_payment": _format_financing_value(down_payment, "$"),
            "interest_rate": _format_financing_value(interest_rate, suffix="%"),
            "term_years": _format_financing_value(term_years, suffix=" years"),
            "monthly_payment": _format_financing_value(monthly_payment, "$"),
        }
        # Treat fully empty financing payloads as missing data for template display.
        if all(
            value is None
            for value in [down_payment, interest_rate, term_years, monthly_payment]
        ):
            financing = None

    hold_years_default = cast(int, settings.FINANCE_DEFAULTS.get("hold_years", 5))
    exit_cap_rate_default = cast(
        Decimal, settings.FINANCE_DEFAULTS.get("exit_cap_rate", Decimal("0.06"))
    )
    exit_cap_rate_value = analysis.exit_cap_rate if analysis else exit_cap_rate_default

    context = {
        "property": property_obj,
        "property_type": (
            f"Multi-family ({property_obj.units} units)"
            if property_obj.units > 1
            else "Single-family"
        ),
        "analysis": analysis,
        "rental_income": rental_income,
        "effective_gross_income": effective_gross_income,
        "operating_expenses": property_obj.operating_expenses.order_by(
            "category", "id"
        ),
        "financing": financing,
        "assumptions": {
            "vacancy_rate": vacancy_rate,
            "vacancy_rate_pct": vacancy_rate * Decimal("100"),
            "hold_years": analysis.hold_years if analysis else hold_years_default,
            "exit_cap_rate": exit_cap_rate_value,
            "exit_cap_rate_pct": exit_cap_rate_value * Decimal("100"),
        },
        "generated_date": timezone.now(),
    }

    html = render_to_string("exports/deal_summary.html", context)

    try:
        pdf_bytes = _generate_pdf(html)
    except Exception as exc:
        logger.error(
            "PDF generation failed for property_id=%s: %s",
            property_obj.pk,
            exc,
        )
        return HttpResponse(
            "Unable to generate PDF. Please contact support if this issue persists.",
            status=500,
        )

    filename = f"deal-summary-{slugify(property_obj.address) or property_obj.pk}.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
