from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory

from core.decorators import is_rate_limited, rate_limit


def _clear_cache():
    cache.clear()


def test_is_rate_limited_allows_under_limit(user):
    _clear_cache()
    request = RequestFactory().get("/")
    request.user = user

    for _ in range(3):
        assert is_rate_limited(request, "test_key", limit=3, window_seconds=60) is False


def test_is_rate_limited_blocks_over_limit(user):
    _clear_cache()
    request = RequestFactory().get("/")
    request.user = user

    for _ in range(3):
        is_rate_limited(request, "test_key2", limit=3, window_seconds=60)

    assert is_rate_limited(request, "test_key2", limit=3, window_seconds=60) is True


def test_is_rate_limited_keys_are_per_user(user, second_user):
    _clear_cache()
    request_a = RequestFactory().get("/")
    request_a.user = user
    request_b = RequestFactory().get("/")
    request_b.user = second_user

    for _ in range(3):
        is_rate_limited(request_a, "test_key3", limit=3, window_seconds=60)

    # A different user's requests aren't affected by user A's usage.
    assert is_rate_limited(request_b, "test_key3", limit=3, window_seconds=60) is False


def test_rate_limit_decorator_returns_429_over_limit(user):
    _clear_cache()

    @rate_limit("test_decorator", limit=1, window_seconds=60)
    def view(request):
        return HttpResponse("ok")

    request = RequestFactory().get("/")
    request.user = user

    first = view(request)
    second = view(request)

    assert first.status_code == 200
    assert second.status_code == 429
