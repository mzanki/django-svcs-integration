"""Type contracts checked by ``uv run mypy``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, assert_type

import django_svcs


if TYPE_CHECKING:
    from asyncio import Future
    from collections.abc import Callable, Coroutine
    from typing import Any

    from django.http import HttpRequest, HttpResponse, StreamingHttpResponse


class Service(Protocol):
    def ping(self) -> str: ...


class Implementation:
    def ping(self) -> str:
        return "ok"


def check_sync(request: HttpRequest) -> None:
    django_svcs.register_factory(Service, Implementation)
    django_svcs.register_value(Service, Implementation())
    django_svcs.bind_local_factory(request, Service, Implementation)
    django_svcs.bind_local_value(request, Service, Implementation())
    django_svcs.overwrite_factory(request, Service, Implementation)
    django_svcs.overwrite_value(request, Service, Implementation())
    assert_type(django_svcs.get(request, Service), Service)
    assert_type(django_svcs.get(request, Service, int), tuple[Service, int])


async def check_async(request: HttpRequest) -> None:
    assert_type(await django_svcs.aget(request, Service), Service)
    assert_type(await django_svcs.aget(request, Service, int), tuple[Service, int])


def check_sync_middleware(
    request: HttpRequest,
    get_response: Callable[[HttpRequest], HttpResponse],
    get_stream: Callable[[HttpRequest], StreamingHttpResponse],
) -> None:
    assert_type(django_svcs.SvcsMiddleware(get_response)(request), HttpResponse)
    assert_type(django_svcs.SvcsMiddleware(get_stream)(request), StreamingHttpResponse)


async def check_async_middleware(
    request: HttpRequest,
    get_response: Callable[[HttpRequest], Coroutine[Any, Any, HttpResponse]],
    get_stream: Callable[[HttpRequest], Coroutine[Any, Any, StreamingHttpResponse]],
) -> None:
    assert_type(await django_svcs.SvcsMiddleware(get_response)(request), HttpResponse)
    assert_type(await django_svcs.SvcsMiddleware(get_stream)(request), StreamingHttpResponse)


def check_future_middleware(
    request: HttpRequest,
    get_response: Callable[[HttpRequest], Future[HttpResponse]],
) -> None:
    # A coroutine-marked callback may return a Future, but middleware wraps it.
    response = django_svcs.SvcsMiddleware(get_response)(request)
    assert_type(response, Coroutine[Any, Any, HttpResponse]).close()
