from io import BytesIO

from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader

from core.models import Transaction


def test_pdf_export_returns_200(client, user, property_sfr, analysis_sfr):
    client.force_login(user)

    response = client.get(
        reverse("property_export_pdf", kwargs={"pk": property_sfr.pk})
    )

    assert response.status_code == 200
    assert response["Content-Disposition"].startswith(
        'attachment; filename="deal-summary-'
    )
    assert response.content.startswith(b"%PDF-")


def test_pdf_export_content_type_is_pdf(client, user, property_sfr, analysis_sfr):
    client.force_login(user)

    response = client.get(
        reverse("property_export_pdf", kwargs={"pk": property_sfr.pk})
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"


def test_pdf_export_404_for_wrong_user(client, user, property_owned_by_second_user):
    client.force_login(user)

    response = client.get(
        reverse("property_export_pdf", kwargs={"pk": property_owned_by_second_user.pk})
    )

    assert response.status_code == 404


def test_pdf_export_includes_financing_section(
    client, user, property_sfr, analysis_sfr
):
    Transaction.objects.create(
        property=property_sfr,
        type=Transaction.Type.LOAN,
        amount=200000,
        date=property_sfr.purchase_date or timezone.now().date(),
        metadata={
            "downPayment": "50000",
            "interestRate": "6.5",
            "loanTermYears": 30,
            "monthlyPayment": "1264.81",
        },
    )
    client.force_login(user)

    response = client.get(
        reverse("property_export_pdf", kwargs={"pk": property_sfr.pk})
    )

    reader = PdfReader(BytesIO(response.content))
    extracted_text = " ".join(page.extract_text() or "" for page in reader.pages)

    assert response.status_code == 200
    assert "Financing" in extracted_text
    assert "$50,000.00" in extracted_text


def test_pdf_export_returns_500_on_generation_failure(
    client, user, property_sfr, analysis_sfr, monkeypatch
):
    monkeypatch.setattr(
        "core.views._generate_pdf",
        lambda html: (_ for _ in ()).throw(Exception("Playwright error")),
    )
    client.force_login(user)

    response = client.get(
        reverse("property_export_pdf", kwargs={"pk": property_sfr.pk})
    )

    assert response.status_code == 500
