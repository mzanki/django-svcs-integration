from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import StreamingHttpResponse

from asgiref.sync import iscoroutinefunction, markcoroutinefunction


if TYPE_CHECKING:
    from collections.abc import AsyncIterable, Awaitable, Callable, Iterable

    from django.http import HttpRequest, HttpResponseBase


_REQUEST_ATTR = "svcs_container"


class SvcsMiddleware:
    """
    Attach a fresh :class:`svcs.Container` to each request and close it when
    the response is done.

    Streaming responses are wrapped so cleanup runs after the body is fully
    consumed. Sync and async views are both supported via the standard
    Django hybrid middleware pattern.
    """

    sync_capable = True
    async_capable = True

    def __init__(
        self,
        get_response: Callable[[HttpRequest], HttpResponseBase] | Callable[[HttpRequest], Awaitable[HttpResponseBase]],
    ) -> None:
        self.get_response = get_response
        self._is_async = iscoroutinefunction(get_response)
        if self._is_async:
            markcoroutinefunction(self)

    def __call__(self, request: HttpRequest) -> HttpResponseBase | Awaitable[HttpResponseBase]:
        if self._is_async:
            return self.__acall__(request)
        return self._sync_call(request)

    def _sync_call(self, request: HttpRequest) -> HttpResponseBase:
        try:
            response = self.get_response(request)  # type: ignore[misc]
        except BaseException:
            _close_sync(request)
            raise

        if isinstance(response, StreamingHttpResponse):
            response.streaming_content = _wrap_streaming_sync(response.streaming_content, request)
        else:
            _close_sync(request)
        return response

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        try:
            response = await self.get_response(request)  # type: ignore[misc]
        except BaseException:
            await _close_async(request)
            raise

        if isinstance(response, StreamingHttpResponse):
            response.streaming_content = _wrap_streaming_async(response.streaming_content, request)
        else:
            await _close_async(request)
        return response


def _pop_container(request: HttpRequest):
    container = getattr(request, _REQUEST_ATTR, None)
    if container is not None:
        delattr(request, _REQUEST_ATTR)
    return container


def _close_sync(request: HttpRequest) -> None:
    container = _pop_container(request)
    if container is not None:
        container.close()


async def _close_async(request: HttpRequest) -> None:
    container = _pop_container(request)
    if container is not None:
        await container.aclose()


def _wrap_streaming_sync(iterable: Iterable[bytes], request: HttpRequest) -> Iterable[bytes]:
    def _iter():
        try:
            yield from iterable
        finally:
            _close_sync(request)

    return _iter()


def _wrap_streaming_async(
    iterable: Iterable[bytes] | AsyncIterable[bytes], request: HttpRequest
) -> AsyncIterable[bytes]:
    async def _aiter():
        try:
            if hasattr(iterable, "__aiter__"):
                async for chunk in iterable:  # type: ignore[union-attr]
                    yield chunk
            else:
                for chunk in iterable:  # type: ignore[union-attr]
                    yield chunk
        finally:
            await _close_async(request)

    return _aiter()
