from __future__ import annotations

import sys
from collections.abc import AsyncIterable
from inspect import iscoroutinefunction, markcoroutinefunction
from typing import TYPE_CHECKING, Any, Final, cast, overload

from django.http import StreamingHttpResponse


if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine, Iterable, Iterator
    from types import TracebackType

    from django.http import HttpRequest, HttpResponseBase

    import svcs

    _ExcInfo = tuple[type[BaseException] | None, BaseException | None, TracebackType | None]


_REQUEST_ATTR = "svcs_container"
_EXCEPTION_ATTR = "_svcs_exception_info"


class SvcsMiddleware[ResponseT: HttpResponseBase | Awaitable[HttpResponseBase]]:
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
        get_response: Callable[[HttpRequest], ResponseT],
    ) -> None:
        self.get_response: Final = get_response
        self._is_async = iscoroutinefunction(get_response)
        if self._is_async:
            markcoroutinefunction(self)

    @overload
    def __call__[R: HttpResponseBase](
        self: SvcsMiddleware[Awaitable[R]], request: HttpRequest
    ) -> Coroutine[Any, Any, R]: ...

    @overload
    def __call__[R: HttpResponseBase](self: SvcsMiddleware[R], request: HttpRequest) -> R: ...

    def __call__(self, request: HttpRequest) -> HttpResponseBase | Coroutine[Any, Any, HttpResponseBase]:
        if self._is_async:
            return self.__acall__(request)
        return self._sync_call(request)

    def process_exception(self, request: HttpRequest, exception: Exception) -> None:
        # Django converts view exceptions into responses before teardown.
        setattr(request, _EXCEPTION_ATTR, (type(exception), exception, exception.__traceback__))

    def _sync_call(self, request: HttpRequest) -> HttpResponseBase:
        try:
            response = cast("HttpResponseBase", self.get_response(request))
        except BaseException:
            _close_sync(request, sys.exc_info())
            raise

        if isinstance(response, StreamingHttpResponse):
            content = response.streaming_content
            response.streaming_content = (
                _wrap_streaming_async(content, request)
                if isinstance(content, AsyncIterable)
                else _wrap_streaming_sync(content, request)
            )
        else:
            _close_sync(request)
        return response

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        try:
            response = await cast("Awaitable[HttpResponseBase]", self.get_response(request))
        except BaseException:
            await _close_async(request, sys.exc_info())
            raise

        if isinstance(response, StreamingHttpResponse):
            response.streaming_content = _wrap_streaming_async(response.streaming_content, request)
        else:
            await _close_async(request)
        return response


def _pop_container(request: HttpRequest) -> svcs.Container | None:
    container = cast("svcs.Container | None", getattr(request, _REQUEST_ATTR, None))
    if container is not None:
        delattr(request, _REQUEST_ATTR)
    return container


def _close_sync(request: HttpRequest, exc_info: _ExcInfo | None = None) -> None:
    container = _pop_container(request)
    saved_exc_info = request.__dict__.pop(_EXCEPTION_ATTR, (None, None, None))
    if container is not None:
        container.close(*(exc_info if exc_info is not None else saved_exc_info))


async def _close_async(request: HttpRequest, exc_info: _ExcInfo | None = None) -> None:
    container = _pop_container(request)
    saved_exc_info = request.__dict__.pop(_EXCEPTION_ATTR, (None, None, None))
    if container is not None:
        await container.aclose(*(exc_info if exc_info is not None else saved_exc_info))


def _wrap_streaming_sync(iterable: Iterable[bytes], request: HttpRequest) -> Iterable[bytes]:
    def _iter() -> Iterator[bytes]:
        exc_info = None
        try:
            yield from iterable
        except BaseException:
            exc_info = sys.exc_info()
            raise
        finally:
            _close_sync(request, exc_info)

    return _iter()


def _wrap_streaming_async(
    iterable: Iterable[bytes] | AsyncIterable[bytes], request: HttpRequest
) -> AsyncIterable[bytes]:
    async def _aiter() -> AsyncIterator[bytes]:
        exc_info = None
        try:
            if isinstance(iterable, AsyncIterable):
                async for chunk in iterable:
                    yield chunk
            else:
                for chunk in iterable:
                    yield chunk
        except BaseException:
            exc_info = sys.exc_info()
            raise
        finally:
            await _close_async(request, exc_info)

    return _aiter()
