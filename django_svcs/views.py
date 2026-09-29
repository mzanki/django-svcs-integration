from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import JsonResponse
from django.views import View

from ._container import get_pings


if TYPE_CHECKING:
    from django.http import HttpRequest


def _format(healthy: list[str], failing: dict[str, str]) -> JsonResponse:
    status = 200 if not failing else 503
    return JsonResponse({"healthy": healthy, "failing": failing}, status=status)


class HealthCheckView(View):
    """
    Run all registered sync service pings and return JSON with per-service status.

    Returns ``200`` if every ping succeeds, ``503`` otherwise. Payload shape:
    ``{"healthy": [<name>...], "failing": {<name>: <error>...}}``.

    For ASGI deployments with async pings, use :class:`AsyncHealthCheckView`.
    Wire it via ``path("health/", HealthCheckView.as_view())``.
    """

    http_method_names = ["get", "head", "options"]

    def get(self, request: HttpRequest) -> JsonResponse:
        healthy: list[str] = []
        failing: dict[str, str] = {}
        for ping in get_pings(request):
            try:
                ping.ping()
            except Exception as exc:
                failing[ping.name] = repr(exc)
            else:
                healthy.append(ping.name)
        return _format(healthy, failing)


class AsyncHealthCheckView(View):
    """
    Async variant of :class:`HealthCheckView` for ASGI deployments. Awaits
    every ping via :meth:`svcs.ServicePing.aping`, so both sync and async
    pings work.
    """

    http_method_names = ["get", "head", "options"]

    async def get(self, request: HttpRequest) -> JsonResponse:
        healthy: list[str] = []
        failing: dict[str, str] = {}
        for ping in get_pings(request):
            try:
                await ping.aping()
            except Exception as exc:
                failing[ping.name] = repr(exc)
            else:
                healthy.append(ping.name)
        return _format(healthy, failing)
