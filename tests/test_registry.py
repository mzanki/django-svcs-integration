from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass

from django.test import RequestFactory, TestCase

import svcs

import django_svcs


class Database:
    pass


class Cache:
    pass


@dataclass
class Handler:
    database: Database


class GetRegistryTests(TestCase):
    def test_returns_singleton(self):
        self.assertIs(django_svcs.get_registry(), django_svcs.get_registry())

    def test_returns_svcs_registry(self):
        self.assertIsInstance(django_svcs.get_registry(), svcs.Registry)


class RegisterFactoryTests(TestCase):
    def tearDown(self):
        django_svcs.get_registry()._services.pop(Database, None)

    def test_factory_round_trip(self):
        django_svcs.register_factory(Database, Database)

        con = svcs.Container(django_svcs.get_registry())
        try:
            db = con.get(Database)
        finally:
            con.close()

        self.assertIsInstance(db, Database)

    def test_factory_ping_surfaces_in_get_pings(self):
        django_svcs.register_factory(Database, Database, ping=lambda _svc: None)

        con = svcs.Container(django_svcs.get_registry())
        try:
            names = [p.name for p in con.get_pings()]
        finally:
            con.close()

        self.assertIn("tests.test_registry.Database", names)


class RegisterValueTests(TestCase):
    def tearDown(self):
        django_svcs.get_registry()._services.pop(Cache, None)

    def test_value_round_trip(self):
        sentinel = Cache()
        django_svcs.register_value(Cache, sentinel)

        con = svcs.Container(django_svcs.get_registry())
        try:
            self.assertIs(con.get(Cache), sentinel)
        finally:
            con.close()


class BindLocalTests(TestCase):
    """Per-request bindings via ``bind_local_value`` / ``bind_local_factory``.

    These bind on the request's container's *local* registry; the
    process-wide registry stays untouched, unlike ``overwrite_*``.
    """

    def _make_request(self):
        from django.test import RequestFactory

        return RequestFactory().get("/")

    def test_bind_local_value_visible_only_on_request_container(self):
        request = self._make_request()
        sentinel = Cache()

        django_svcs.bind_local_value(request, Cache, sentinel)

        # Same request: sees the binding.
        self.assertIs(django_svcs.svcs_from(request).get(Cache), sentinel)
        # Process registry: NOT polluted by the local binding.
        self.assertNotIn(Cache, django_svcs.get_registry()._services)

    def test_bind_local_factory_builds_per_resolution(self):
        request = self._make_request()
        built: list[Database] = []

        def factory():
            db = Database()
            built.append(db)
            return db

        django_svcs.bind_local_factory(request, Database, factory)

        container = django_svcs.svcs_from(request)
        db1 = container.get(Database)
        db2 = container.get(Database)

        self.assertIs(db1, db2)  # svcs caches per container scope
        self.assertEqual(len(built), 1)
        self.assertNotIn(Database, django_svcs.get_registry()._services)


class FactoryAdapterTests(TestCase):
    """``django_svcs.factory`` lets lambdas register without param-name dance."""

    def tearDown(self):
        django_svcs.get_registry()._services.pop(Database, None)

    def test_lambda_with_short_param_name_works_via_adapter(self):
        # Without the adapter, svcs would call this lambda with zero args
        # because the param name "c" doesn't match "svcs_container".
        django_svcs.register_factory(
            Database,
            django_svcs.factory(lambda c: Database()),
        )

        con = svcs.Container(django_svcs.get_registry())
        try:
            self.assertIsInstance(con.get(Database), Database)
        finally:
            con.close()

    def test_adapter_passes_container_through(self):
        seen: list[svcs.Container] = []

        django_svcs.register_factory(
            Database,
            django_svcs.factory(lambda c: seen.append(c) or Database()),
        )

        con = svcs.Container(django_svcs.get_registry())
        try:
            con.get(Database)
        finally:
            con.close()

        self.assertEqual(len(seen), 1)
        self.assertIs(seen[0], con)


class CloseRegistryTests(TestCase):
    def test_on_registry_close_callback_runs(self):
        # Use a throwaway Registry — calling close_registry() on the process-wide
        # one clears _services and wipes any registrations done by AppConfig.ready(),
        # poisoning subsequent tests in the suite.
        registry = svcs.Registry()
        called: list[int] = []
        registry.register_factory(Database, Database, on_registry_close=lambda: called.append(1))

        registry.close()

        self.assertEqual(called, [1])


class ExceptionRegistrationTests(TestCase):
    def tearDown(self):
        django_svcs.get_registry()._services.pop(Database, None)

    def test_registration_and_overwrite_helpers_forward_cleanup_option(self):
        for name in ("register_factory", "register_value", "overwrite_factory", "overwrite_value"):
            with self.subTest(helper=name):
                errors = []

                @contextmanager
                def resource(errors=errors):
                    try:
                        yield Database()
                    except RuntimeError as exc:
                        errors.append(exc)
                        raise

                request = RequestFactory().get("/")
                kwargs = {"suppress_context_exit": False}
                value = resource
                if name.endswith("value"):
                    value = resource()
                    kwargs["enter"] = True
                args = (request, Database, value) if name.startswith("overwrite") else (Database, value)
                getattr(django_svcs, name)(*args, **kwargs)

                error = RuntimeError("cleanup")
                with self.assertRaises(RuntimeError), django_svcs.svcs_from(request) as container:
                    self.assertIsInstance(container.get(Database), Database)
                    raise error
                self.assertEqual(errors, [error])


class AutowiringTests(TestCase):
    def setUp(self):
        django_svcs.register_factory(Database, Database)

    def tearDown(self):
        registry = django_svcs.get_registry()
        registry._services.pop(Database, None)
        registry._services.pop(Handler, None)

    def test_autowire_resolves_dependencies_from_request_container(self):
        django_svcs.register_factory(Handler, svcs.autowire(Handler))
        request = RequestFactory().get("/")

        with django_svcs.svcs_from(request):
            handler = django_svcs.get(request, Handler)
            self.assertIs(handler.database, django_svcs.get(request, Database))

    async def test_aautowire_uses_local_bindings_and_cleans_up_async_dependencies(self):
        closed = []

        async def database():
            yield Database()
            closed.append(True)

        request = RequestFactory().get("/")
        django_svcs.bind_local_factory(request, Database, database)
        django_svcs.bind_local_factory(request, Handler, svcs.aautowire(Handler))

        async with django_svcs.svcs_from(request):
            handler = await django_svcs.aget(request, Handler)
            self.assertIs(handler.database, await django_svcs.aget(request, Database))
            self.assertEqual(closed, [])
        self.assertEqual(closed, [True])
