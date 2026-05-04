import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def user(db):
    User = get_user_model()
    return User.objects.create_user(
        username="tester", email="tester@example.com", password="pass"
    )
