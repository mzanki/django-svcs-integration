from __future__ import annotations

from typing import TYPE_CHECKING, Any, overload

import svcs
from svcs._core import T1, T2, T3, T4, T5, T6, T7, T8, T9, T10

from ._registry import get_registry


if TYPE_CHECKING:
    from django.http import HttpRequest


_REQUEST_ATTR = "svcs_container"


def svcs_from(request: HttpRequest) -> svcs.Container:
    """
    Return the :class:`svcs.Container` attached to *request*, creating one
    lazily if absent.

    The container lives for the duration of the request; cleanup is the
    responsibility of :class:`django_svcs.SvcsMiddleware`. If the middleware
    is not installed, callers must close the container themselves.
    """
    container = getattr(request, _REQUEST_ATTR, None)
    if container is None:
        container = svcs.Container(get_registry())
        setattr(request, _REQUEST_ATTR, container)
    return container


@overload
def get(request: HttpRequest, svc_type: type[T1], /) -> T1: ...


@overload
def get(request: HttpRequest, svc_type1: type[T1], svc_type2: type[T2], /) -> tuple[T1, T2]: ...


@overload
def get(
    request: HttpRequest, svc_type1: type[T1], svc_type2: type[T2], svc_type3: type[T3], /
) -> tuple[T1, T2, T3]: ...


@overload
def get(
    request: HttpRequest,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    /,
) -> tuple[T1, T2, T3, T4]: ...


@overload
def get(
    request: HttpRequest,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    /,
) -> tuple[T1, T2, T3, T4, T5]: ...


@overload
def get(
    request: HttpRequest,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    svc_type6: type[T6],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6]: ...


@overload
def get(
    request: HttpRequest,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    svc_type6: type[T6],
    svc_type7: type[T7],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7]: ...


@overload
def get(
    request: HttpRequest,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    svc_type6: type[T6],
    svc_type7: type[T7],
    svc_type8: type[T8],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8]: ...


@overload
def get(
    request: HttpRequest,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    svc_type6: type[T6],
    svc_type7: type[T7],
    svc_type8: type[T8],
    svc_type9: type[T9],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9]: ...


@overload
def get(
    request: HttpRequest,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    svc_type6: type[T6],
    svc_type7: type[T7],
    svc_type8: type[T8],
    svc_type9: type[T9],
    svc_type10: type[T10],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9, T10]: ...


def get(request: HttpRequest, *svc_types: type) -> object:
    """
    Resolve one or more services from the container attached to *request*.

    See Also:
        :meth:`svcs.Container.get`
    """
    return svcs_from(request).get(*svc_types)


def get_abstract(request: HttpRequest, *svc_types: type) -> Any:
    """
    Resolve abstract service types from the container attached to *request*.

    See Also:
        :meth:`svcs.Container.get_abstract`
    """
    return svcs_from(request).get_abstract(*svc_types)


@overload
async def aget(request: HttpRequest, svc_type: type[T1], /) -> T1: ...


@overload
async def aget(request: HttpRequest, svc_type1: type[T1], svc_type2: type[T2], /) -> tuple[T1, T2]: ...


@overload
async def aget(
    request: HttpRequest, svc_type1: type[T1], svc_type2: type[T2], svc_type3: type[T3], /
) -> tuple[T1, T2, T3]: ...


@overload
async def aget(
    request: HttpRequest,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    /,
) -> tuple[T1, T2, T3, T4]: ...


@overload
async def aget(
    request: HttpRequest,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    /,
) -> tuple[T1, T2, T3, T4, T5]: ...


@overload
async def aget(
    request: HttpRequest,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    svc_type6: type[T6],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6]: ...


@overload
async def aget(
    request: HttpRequest,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    svc_type6: type[T6],
    svc_type7: type[T7],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7]: ...


@overload
async def aget(
    request: HttpRequest,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    svc_type6: type[T6],
    svc_type7: type[T7],
    svc_type8: type[T8],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8]: ...


@overload
async def aget(
    request: HttpRequest,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    svc_type6: type[T6],
    svc_type7: type[T7],
    svc_type8: type[T8],
    svc_type9: type[T9],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9]: ...


@overload
async def aget(
    request: HttpRequest,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    svc_type6: type[T6],
    svc_type7: type[T7],
    svc_type8: type[T8],
    svc_type9: type[T9],
    svc_type10: type[T10],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9, T10]: ...


async def aget(request: HttpRequest, *svc_types: type) -> object:
    """
    Async-resolve one or more services from the container attached to *request*.

    See Also:
        :meth:`svcs.Container.aget`
    """
    return await svcs_from(request).aget(*svc_types)


async def aget_abstract(request: HttpRequest, *svc_types: type) -> Any:
    """
    Async-resolve abstract service types from the container attached to *request*.

    See Also:
        :meth:`svcs.Container.aget_abstract`
    """
    return await svcs_from(request).aget_abstract(*svc_types)


def get_pings(request: HttpRequest) -> list[svcs.ServicePing]:
    """
    Return all :class:`svcs.ServicePing` instances for services registered
    with a ping callable.

    See Also:
        :meth:`svcs.Container.get_pings`
    """
    return svcs_from(request).get_pings()
