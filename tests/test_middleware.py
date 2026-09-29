"""
Tests for ``django_svcs.middleware.SvcsMiddleware``.

Three test classes covering the three execution paths:

- ``SvcsMiddlewareSyncTests`` — sync view + container close after response.
- ``SvcsMiddlewareAsyncTests`` — async view + ``markcoroutinefunction`` flag.
- ``SvcsMiddlewareStreamingTests`` — sync + async ``StreamingHttpResponse``
  cleanup ordering (cleanup runs after iteration completes, not before).
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, contextmanager
from inspect import iscoroutinefunction, markcoroutinefunction

from django.http import HttpResponse, StreamingHttpResponse
from django.test import RequestFactory, TestCase, override_settings

import django_svcs
from django_svcs.middleware import SvcsMiddleware

from tests._fixtures.views import Service


MIDDLEWARE = ["django_svcs.middleware.SvcsMiddleware"]


@override_settings(MIDDLEWARE=MIDDLEWARE)
class SvcsMiddlewareSyncTests(TestCase):
    def setUp(self):
        self.factory_calls: list[int] = []
        self.cleanup_calls: list[int] = []

        def factory():
            self.factory_calls.append(1)
            yield Service("built")
            self.cleanup_calls.append(1)

        django_svcs.register_factory(Service, factory)

    def tearDown(self):
        django_svcs.get_registry()._services.pop(Service, None)

    def test_container_attached_and_closed(self):
        response = self.client.get("/_fixtures/svc/abc/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"abc:built")
        self.assertEqual(self.factory_calls, [1])
        self.assertEqual(self.cleanup_calls, [1])

    def test_container_not_created_when_unused(self):
        response = self.client.get("/_fixtures/ok/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.factory_calls, [])

    def test_cleanup_runs_when_view_raises(self):
        with self.assertRaises(RuntimeError):
            self.client.get("/_fixtures/raise/")

        self.assertEqual(self.factory_calls, [])

    def test_each_request_gets_fresh_container(self):
        self.client.get("/_fixtures/svc/a/")
        self.client.get("/_fixtures/svc/b/")

        self.assertEqual(self.factory_calls, [1, 1])
        self.assertEqual(self.cleanup_calls, [1, 1])


@override_settings(MIDDLEWARE=MIDDLEWARE)
class SvcsMiddlewareAsyncTests(TestCase):
    def setUp(self):
        self.cleanup_calls: list[int] = []

        async def factory():
            yield Service("async")
            self.cleanup_calls.append(1)

        django_svcs.register_factory(Service, factory)

    def tearDown(self):
        django_svcs.get_registry()._services.pop(Service, None)

    async def test_async_view_resolves_via_aget(self):
        response = await self.async_client.get("/_fixtures/aget/zz/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"zz:async")
        self.assertEqual(self.cleanup_calls, [1])

    async def test_marked_future_handler_returns_coroutine_and_cleans_up(self):
        request = RequestFactory().get("/")
        await django_svcs.aget(request, Service)
        expected = HttpResponse("ok")

        @markcoroutinefunction
        def get_response(request):
            future = asyncio.get_running_loop().create_future()
            future.set_result(expected)
            return future

        instance = SvcsMiddleware(get_response)
        response = instance(request)

        self.assertTrue(iscoroutinefunction(instance))
        self.assertTrue(asyncio.iscoroutine(response))
        self.assertIs(await response, expected)
        self.assertEqual(self.cleanup_calls, [1])
        self.assertFalse(hasattr(request, "svcs_container"))


class MiddlewareCoroutineFlagTests(TestCase):
    def test_marks_instance_async_when_get_response_is_async(self):
        async def get_response(request):
            return None

        instance = SvcsMiddleware(get_response)

        self.assertTrue(iscoroutinefunction(instance))

    def test_sync_get_response_is_not_marked_async(self):
        def get_response(request):
            return None

        instance = SvcsMiddleware(get_response)

        self.assertFalse(iscoroutinefunction(instance))


@override_settings(MIDDLEWARE=MIDDLEWARE)
class SvcsMiddlewareStreamingTests(TestCase):
    def setUp(self):
        self.events: list[str] = []

        def factory():
            yield Service("stream")
            self.events.append("cleanup")

        django_svcs.register_factory(Service, factory)

    def tearDown(self):
        django_svcs.get_registry()._services.pop(Service, None)

    def test_sync_cleanup_runs_after_iteration(self):
        response = self.client.get("/_fixtures/stream/")

        chunks: list[bytes] = []
        for chunk in response.streaming_content:
            chunks.append(chunk)
            self.events.append(f"chunk:{chunk.decode()}")

        self.assertEqual(b"".join(chunks), b"sbc")
        self.assertEqual(
            self.events,
            ["chunk:s", "chunk:b", "chunk:c", "cleanup"],
        )

    async def test_async_iterator_under_sync_middleware_closes_after_iteration(self):
        async def stream():
            yield b"first"
            yield b"last"

        def get_response(request):
            django_svcs.get(request, Service)
            return StreamingHttpResponse(stream())

        request = RequestFactory().get("/")
        response = SvcsMiddleware(get_response)(request)
        self.assertTrue(response.is_async)
        self.assertEqual(self.events, [])

        async for chunk in response.streaming_content:
            self.events.append(chunk.decode())

        self.assertEqual(self.events, ["first", "last", "cleanup"])
        self.assertFalse(hasattr(request, "svcs_container"))


@override_settings(MIDDLEWARE=MIDDLEWARE)
class AsyncSvcsMiddlewareStreamingTests(TestCase):
    def setUp(self):
        self.events: list[str] = []

        async def factory():
            yield Service("astream")
            self.events.append("cleanup")

        django_svcs.register_factory(Service, factory)

    def tearDown(self):
        django_svcs.get_registry()._services.pop(Service, None)

    async def test_async_cleanup_runs_after_iteration(self):
        response = await self.async_client.get("/_fixtures/astream/")

        chunks: list[bytes] = []
        async for chunk in response.streaming_content:
            chunks.append(chunk)
            self.events.append(f"chunk:{chunk.decode()}")

        self.assertEqual(b"".join(chunks), b"ayz")
        self.assertEqual(
            self.events,
            ["chunk:a", "chunk:y", "chunk:z", "cleanup"],
        )

    async def test_sync_iterator_under_async_middleware_closes_after_iteration(self):
        async def get_response(request):
            await django_svcs.aget(request, Service)
            return StreamingHttpResponse(iter([b"first", b"last"]))

        response = await SvcsMiddleware(get_response)(RequestFactory().get("/"))
        self.assertEqual(self.events, [])

        async for chunk in response.streaming_content:
            self.events.append(chunk.decode())

        self.assertEqual(self.events, ["first", "last", "cleanup"])


@override_settings(MIDDLEWARE=MIDDLEWARE)
class ExceptionCleanupTests(TestCase):
    def setUp(self):
        self.errors: list[BaseException | None] = []
        self.tracebacks = []

    def tearDown(self):
        django_svcs.get_registry()._services.pop(Service, None)

    @contextmanager
    def resource(self):
        try:
            yield Service()
        except BaseException as exc:
            self.errors.append(exc)
            self.tracebacks.append(exc.__traceback__)
            raise
        else:
            self.errors.append(None)

    @asynccontextmanager
    async def async_resource(self):
        with self.resource() as service:
            yield service

    def test_view_exception_reaches_opted_in_cleanup(self):
        django_svcs.register_factory(Service, self.resource, suppress_context_exit=False)

        with self.assertRaisesRegex(RuntimeError, "boom") as raised:
            self.client.get("/_fixtures/raise-service/")

        self.assertEqual(self.errors, [raised.exception])
        self.assertIsNotNone(self.tracebacks[0])

    async def test_async_view_exception_reaches_opted_in_cleanup(self):
        django_svcs.register_factory(Service, self.async_resource, suppress_context_exit=False)

        with self.assertRaisesRegex(RuntimeError, "boom") as raised:
            await self.async_client.get("/_fixtures/araise-service/")

        self.assertEqual(self.errors, [raised.exception])

    def test_default_cleanup_still_suppresses_exception_context(self):
        django_svcs.register_factory(Service, self.resource)

        with self.assertRaisesRegex(RuntimeError, "boom"):
            self.client.get("/_fixtures/raise-service/")

        self.assertEqual(self.errors, [None])

    async def test_async_default_cleanup_still_suppresses_exception_context(self):
        django_svcs.register_factory(Service, self.async_resource)

        with self.assertRaisesRegex(RuntimeError, "boom"):
            await self.async_client.get("/_fixtures/araise-service/")

        self.assertEqual(self.errors, [None])

    def test_successful_request_has_no_exception_context(self):
        django_svcs.register_factory(Service, self.resource, suppress_context_exit=False)

        self.assertEqual(self.client.get("/_fixtures/svc/ok/").status_code, 200)
        self.assertEqual(self.errors, [None])

    def test_direct_exception_reaches_cleanup_and_is_reraised(self):
        django_svcs.register_factory(Service, self.resource, suppress_context_exit=False)
        error = RuntimeError("direct")

        def get_response(request):
            django_svcs.get(request, Service)
            raise error

        request = RequestFactory().get("/")
        with self.assertRaises(RuntimeError):
            SvcsMiddleware(get_response)(request)
        self.assertEqual(self.errors, [error])
        self.assertFalse(hasattr(request, "svcs_container"))

    async def test_async_cancellation_reaches_cleanup(self):
        from asyncio import CancelledError

        django_svcs.register_factory(Service, self.async_resource, suppress_context_exit=False)
        error = CancelledError()

        async def get_response(request):
            await django_svcs.aget(request, Service)
            raise error

        with self.assertRaises(CancelledError):
            await SvcsMiddleware(get_response)(RequestFactory().get("/"))
        self.assertEqual(self.errors, [error])

    def test_stream_exception_reaches_cleanup(self):
        django_svcs.register_factory(Service, self.resource, suppress_context_exit=False)
        error = RuntimeError("stream")

        def get_response(request):
            django_svcs.get(request, Service)

            def body():
                yield b"first"
                raise error

            return StreamingHttpResponse(body())

        response = SvcsMiddleware(get_response)(RequestFactory().get("/"))
        self.assertEqual(self.errors, [])
        with self.assertRaises(RuntimeError):
            list(response.streaming_content)
        self.assertEqual(self.errors, [error])

    async def test_async_stream_exception_reaches_cleanup(self):
        django_svcs.register_factory(Service, self.async_resource, suppress_context_exit=False)
        error = RuntimeError("stream")

        async def get_response(request):
            await django_svcs.aget(request, Service)

            async def body():
                yield b"first"
                raise error

            return StreamingHttpResponse(body())

        response = await SvcsMiddleware(get_response)(RequestFactory().get("/"))
        self.assertEqual(self.errors, [])
        with self.assertRaises(RuntimeError):
            async for _ in response.streaming_content:
                pass
        self.assertEqual(self.errors, [error])
