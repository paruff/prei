from django.urls import reverse


def test_pdf_export_returns_200(client, user, property_sfr, analysis_sfr):
    client.force_login(user)

    response = client.get(
        reverse("property_export_pdf", kwargs={"pk": property_sfr.pk})
    )

    assert response.status_code == 200
    assert response["Content-Disposition"].startswith(
        'attachment; filename="deal-summary-'
    )


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
