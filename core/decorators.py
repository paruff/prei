"""Shared view decorators.

rate_limit / is_rate_limited guard views that fan out to paid, metered
third-party APIs (Rentometer, HUD FMR, ATTOM via screen_property) so a user
can't trigger an unbounded burst of outbound calls through repeated
re-screens or previews.
"""

from __future__ import annotations

import functools
from collections.abc import Callable

from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse


def _increment(key: str, window_seconds: int) -> int:
    """Atomically increment a fixed-window counter, creating it if absent."""
    cache.add(key, 0, timeout=window_seconds)
    return cache.incr(key)


def is_rate_limited(
    request: HttpRequest, key_prefix: str, limit: int, window_seconds: int
) -> bool:
    """True if this user (or IP, if anonymous) is over `limit` hits in the window."""
    identity = (
        request.user.pk
        if request.user.is_authenticated
        else request.META.get("REMOTE_ADDR", "anon")
    )
    count = _increment(f"ratelimit_{key_prefix}_{identity}", window_seconds)
    return count > limit


def rate_limit(
    key_prefix: str, limit: int, window_seconds: int
) -> Callable[[Callable[..., HttpResponse]], Callable[..., HttpResponse]]:
    """Decorator form of is_rate_limited() for views entirely gated by one action."""

    def decorator(
        view_func: Callable[..., HttpResponse],
    ) -> Callable[..., HttpResponse]:
        @functools.wraps(view_func)
        def wrapped(
            request: HttpRequest, *args: object, **kwargs: object
        ) -> HttpResponse:
            if is_rate_limited(request, key_prefix, limit, window_seconds):
                return JsonResponse(
                    {
                        "error": "Too many requests — please wait a few minutes and try again."
                    },
                    status=429,
                )
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
