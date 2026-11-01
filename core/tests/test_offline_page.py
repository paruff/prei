import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_offline_page_is_served_without_login(client):
    """The service worker pre-caches /offline/; a 404 here fails its install."""
    response = client.get(reverse("offline"))
    assert response.status_code == 200
    assert reverse("offline") == "/offline/"
    assert (
        "You&#x27;re Offline" in response.content.decode()
        or "You're Offline" in response.content.decode()
    )
