"""Request cleanup when Django adapts a mixed sync/async middleware stack."""

import asyncio
import threading

from django.http import HttpResponse, StreamingHttpResponse
from django.test import AsyncClient, SimpleTestCase, override_settings
from django.urls import path

from asgiref.sync import sync_to_async

import django_svcs

from tests._fixtures.views import Service, aget_svc, araise_with_service, astream_view, get_svc


class SyncOnlyMiddleware:
    sync_capable = True
    async_capable = False

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)


SVCS_MIDDLEWARE = "django_svcs.middleware.SvcsMiddleware"
SYNC_MIDDLEWARE = f"{__name__}.SyncOnlyMiddleware"
MIXED_STACKS = ([SVCS_MIDDLEWARE, SYNC_MIDDLEWARE], [SYNC_MIDDLEWARE, SVCS_MIDDLEWARE])


async def raw_container_view(request):
    service = await django_svcs.svcs_from(request).aget(Service)
    return HttpResponse(service.label)


async def sync_stream_view(request, fail=False):
    service = await django_svcs.aget(request, Service)

    def chunks():
        yield service.label.encode()
        if fail:
            raise RuntimeError("stream failed")
        yield b"!"

    return StreamingHttpResponse(chunks())


async def cancelled_view(request):
    await django_svcs.aget(request, Service)
    raise asyncio.CancelledError


urlpatterns = [
    path("helper/", aget_svc, {"key": "key"}),
    path("container/", raw_container_view),
    path("error/", araise_with_service),
    path("async-stream/", astream_view),
    path("sync-stream/", sync_stream_view),
    path("stream-error/", sync_stream_view, {"fail": True}),
    path("cancel/", cancelled_view),
    path("sync/", get_svc, {"key": "key"}),
]


@override_settings(ROOT_URLCONF=__name__)
class MixedMiddlewareCleanupTests(SimpleTestCase):
    def setUp(self):
        self.events = []
        self.loops = []
        self.exceptions = []
        events, loops, exceptions = self.events, self.loops, self.exceptions

        # An explicit context manager avoids async-generator finalization masking
        # a missed middleware cleanup.
        class AsyncService:
            async def __aenter__(self):
                events.append("enter")
                loops.append(asyncio.get_running_loop())
                return Service("mixed")

            async def __aexit__(self, exc_type, exc_value, traceback):
                events.append("exit")
                loops.append(asyncio.get_running_loop())
                exceptions.append(exc_value)

        django_svcs.register_factory(Service, AsyncService, suppress_context_exit=False)
        self.addCleanup(django_svcs.get_registry()._services.pop, Service)

    def reset_events(self):
        self.events.clear()
        self.loops.clear()
        self.exceptions.clear()

    def assert_closed_on_request_loop(self):
        self.assertEqual(self.events, ["enter", "exit"])
        self.assertEqual(self.loops, [asyncio.get_running_loop()] * 2)

    async def test_async_cleanup_in_both_middleware_orders(self):
        for middleware in MIXED_STACKS:
            for url in ("/helper/", "/container/"):
                with self.subTest(middleware=middleware, url=url), override_settings(MIDDLEWARE=middleware):
                    self.reset_events()
                    response = await AsyncClient().get(url)

                    self.assertEqual(response.status_code, 200)
                    self.assert_closed_on_request_loop()
                    self.assertEqual(self.exceptions, [None])

    async def test_view_exception_reaches_async_cleanup(self):
        for middleware in MIXED_STACKS:
            with self.subTest(middleware=middleware), override_settings(MIDDLEWARE=middleware):
                self.reset_events()
                with self.assertRaisesMessage(RuntimeError, "boom") as raised:
                    await AsyncClient().get("/error/")

                self.assert_closed_on_request_loop()
                self.assertIs(self.exceptions[0], raised.exception)

    async def test_cancellation_reaches_async_cleanup(self):
        for middleware in MIXED_STACKS:
            with self.subTest(middleware=middleware), override_settings(MIDDLEWARE=middleware):
                self.reset_events()
                with self.assertRaises(asyncio.CancelledError) as raised:
                    await AsyncClient().get("/cancel/")

                self.assert_closed_on_request_loop()
                self.assertIs(self.exceptions[0], raised.exception)

    async def test_stream_cleanup_waits_for_consumption(self):
        for middleware in MIXED_STACKS:
            for url, expected in (("/async-stream/", b"myz"), ("/sync-stream/", b"mixed!")):
                with self.subTest(middleware=middleware, url=url), override_settings(MIDDLEWARE=middleware):
                    self.reset_events()
                    response = await AsyncClient().get(url)
                    self.assertEqual(self.events, ["enter"])

                    if response.is_async:
                        chunks = [chunk async for chunk in response.streaming_content]
                    else:
                        chunks = await sync_to_async(list)(response.streaming_content)

                    self.assertEqual(b"".join(chunks), expected)
                    self.assert_closed_on_request_loop()
                    self.assertEqual(self.exceptions, [None])

    @override_settings(MIDDLEWARE=MIXED_STACKS[0])
    async def test_sync_stream_exception_reaches_async_cleanup(self):
        response = await AsyncClient().get("/stream-error/")
        self.assertEqual(self.events, ["enter"])
        with self.assertRaisesMessage(RuntimeError, "stream failed") as raised:
            await sync_to_async(list)(response.streaming_content)

        self.assert_closed_on_request_loop()
        self.assertIs(self.exceptions[0], raised.exception)

    @override_settings(MIDDLEWARE=MIXED_STACKS[0])
    async def test_sync_cleanup_stays_on_the_factory_thread(self):
        threads = []

        class SyncService:
            def __enter__(self):
                threads.append(threading.get_ident())
                return Service("sync")

            def __exit__(self, *exc_info):
                threads.append(threading.get_ident())

        django_svcs.register_factory(Service, SyncService)
        response = await AsyncClient().get("/sync/")

        self.assertEqual(response.content, b"key:sync")
        self.assertEqual(len(threads), 2)
        self.assertEqual(threads[0], threads[1])
        self.assertNotEqual(threads[0], threading.get_ident())
