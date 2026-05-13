"""
Test fixtures for ``django_svcs`` middleware/streaming/async tests.

Plain Python module — *not* a Django app. The ``Service`` class is a
deliberately trivial stand-in used by the test suite to verify container
wiring, request lifecycle, and streaming cleanup. It does not represent any
real-world service shape — for the architectural example see ``tests/testapp/``.
"""

from __future__ import annotations

from django.http import HttpResponse, StreamingHttpResponse

import django_svcs


class Service:
    """Trivial service used by middleware/streaming/async tests."""

    def __init__(self, label: str = "svc") -> None:
        self.label = label


def get_svc(request, key: str):
    svc = django_svcs.get(request, Service)
    return HttpResponse(f"{key}:{svc.label}")


async def aget_svc(request, key: str):
    svc = await django_svcs.aget(request, Service)
    return HttpResponse(f"{key}:{svc.label}")


def raise_view(request):
    django_svcs.svcs_from(request)
    raise RuntimeError("boom")


def stream_view(request):
    svc = django_svcs.get(request, Service)

    def producer():
        yield svc.label.encode()[:1]
        yield b"b"
        yield b"c"

    return StreamingHttpResponse(producer())


async def astream_view(request):
    svc = await django_svcs.aget(request, Service)

    async def producer():
        yield svc.label.encode()[:1]
        yield b"y"
        yield b"z"

    return StreamingHttpResponse(producer())
