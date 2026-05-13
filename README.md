# django-svcs

A Django integration for [`svcs`](https://github.com/hynek/svcs) — a typed,
late-bound service registry for Python web apps. `svcs` is upstream by Hynek
Schlawack and ships official integrations for Flask, Pyramid, AIOHTTP,
Starlette, and FastAPI; this package is the Django counterpart.

What it gives you:

- A process-wide **Registry** of factory recipes, declared in your `AppConfig`.
- A per-request **Container** that lazily instantiates services and closes
  them when the response (or its streaming body) is done.
- **Per-request bindings** for request-scoped data (current user, tenant,
  request id) without leaking into the process registry.
- **Test-time overrides** via `overwrite_factory` — no `unittest.mock.patch`
  chains.
- A healthcheck CBV that runs every registered ping.

## Install

```bash
pip install git+https://github.com/mzanki/django-svcs.git
```

Or pin a tag/branch:

```bash
pip install git+https://github.com/mzanki/django-svcs.git@v0.1.0
```

## Quickstart

### 1. Wire the app + middleware

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "django_svcs",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django_svcs.middleware.SvcsMiddleware",
    # ...
]
```

### 2. Register services in your `AppConfig.ready()`

```python
# myapp/apps.py
from django.apps import AppConfig

import django_svcs


class MyAppConfig(AppConfig):
    name = "myapp"

    def ready(self) -> None:
        from myapp.payments import PaymentClient, StripeClient

        django_svcs.register_factory(PaymentClient, StripeClient)
```

### 3. Resolve services in views

```python
# myapp/views.py
import django_svcs

from myapp.payments import PaymentClient


def checkout(request):
    payments = django_svcs.get(request, PaymentClient)
    payments.charge(...)
    return ...


async def async_checkout(request):
    payments = await django_svcs.aget(request, PaymentClient)
    ...
```

### 4. Override services in tests

```python
django_svcs.overwrite_factory(request, PaymentClient, FakeStripe)
```

### 5. Bind per-request services from middleware

For values that change *per request* (current user, tenant id, request id),
use the `bind_local_*` helpers — they attach to the request's container
without mutating the process-wide registry:

```python
# myapp/middleware.py
import django_svcs

from myapp.identity import UserContext, ANONYMOUS_USER_CONTEXT


class UserContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ctx = (
            UserContext(user_id=str(request.user.pk), is_authenticated=True)
            if request.user.is_authenticated
            else ANONYMOUS_USER_CONTEXT
        )
        django_svcs.bind_local_value(request, UserContext, ctx)
        return self.get_response(request)
```

That's the whole API surface, day one.

## Public API

| Symbol | Use |
|---|---|
| `register_factory(T, factory, *, enter=True, ping=None, on_registry_close=None)` | Register a factory at boot. Mirrors `svcs.Registry.register_factory`. |
| `register_value(T, value)` | Register a pre-built singleton (no factory call). |
| `get(request, *types)` / `aget(request, *types)` | Resolve up to ten services from the request's container. Returns single value or tuple. |
| `get_abstract(request, T)` / `aget_abstract(request, T)` | Same but for `Protocol` / abstract types. |
| `svcs_from(request)` | Get the raw `svcs.Container` for the request. Lazy-creates if absent. |
| `get_pings(request)` | All registered `ServicePing` instances for healthchecks. |
| `overwrite_factory(request, T, factory)` / `overwrite_value(request, T, value)` | Swap a registration on the **process-wide** registry and reset the cached instance for that request. Test-only — the override leaks into subsequent requests. |
| `bind_local_factory(request, T, factory)` / `bind_local_value(request, T, value)` | Bind a service on **just this request's** container. Use from middleware for per-request scoping. Process registry untouched. |
| `factory(fn)` | Adapter that wraps a lambda or arbitrary callable so svcs's container-introspection always passes the container. |
| `close_registry()` / `aclose_registry()` | Explicit registry shutdown. Mostly useful in ASGI lifespan. |
| `SvcsMiddleware` | The middleware. Attaches `request.svcs_container`, closes on response. |
| `HealthCheckView` / `AsyncHealthCheckView` | CBVs that run all `get_pings()` and return 200/503 JSON. |

## `enter=True` vs `enter=False`

`register_factory` defaults to `enter=True` — if the factory returns a context
manager (or is a generator), svcs **enters** it on resolve and **exits** it on
`container.close()`.

| Who owns the `with` block | Setting |
|---|---|
| The container (cleanup tied to the request lifecycle) | `enter=True` (default) |
| Your own service code (`with self.svc:`) | `enter=False` |

**Two `with`s = bug.** If your service writes `with self.uow:` inside a
method, register the UoW with `enter=False` — otherwise svcs also
enters/exits, producing double-commit / double-rollback.

## `overwrite_factory` vs `bind_local_*` — global vs per-request

Two ways to swap a binding at runtime, easy to confuse:

| | `overwrite_factory` / `overwrite_value` | `bind_local_factory` / `bind_local_value` |
|---|---|---|
| Where the binding lives | **Process-wide registry** | This **request's container only** |
| Survives the current request | **Yes** — leaks into every future request | No — discarded when the request's container closes |
| Use case | Test-time override of a global default | Per-request data (current user, tenant, trace id) |
| Mid-request invariant | Resets the request's cached instance | Lazy — first `container.get(T)` builds with the local binding |

**The footgun:** calling `overwrite_factory` from production middleware (e.g.
to publish a `UserContext`) **permanently rewrites the process registry**, so
subsequent anonymous requests inherit the previous user's binding. Use
`bind_local_*` for anything that varies per request. Reserve `overwrite_*`
for tests where you want a registry-wide swap that gets restored in
`tearDown`.

## Registering lambdas: the `factory` adapter

`svcs` decides whether to pass the container to a factory by **introspecting
its first parameter**: name must be `svcs_container` *or* annotation must be
`svcs.Container`. Lambdas can't carry annotations, and a short param name
like `c` fails the check — `svcs` then calls the lambda with zero arguments
and raises a confusing `TypeError`.

The `factory` adapter wraps any callable so the wrapper's signature
satisfies the check:

```python
import django_svcs

# Without the adapter — svcs would call this with no args:
# django_svcs.register_factory(Handler, lambda c: Handler(c.get(Service)))   # TypeError

# With the adapter — works:
django_svcs.register_factory(
    Handler,
    django_svcs.factory(lambda c: Handler(c.get(Service))),
)
```

Use it whenever you'd otherwise rename a param to `svcs_container` just to
satisfy introspection. The inner callable receives the container unchanged.

## Healthcheck

```python
# urls.py
from django.urls import path
from django_svcs.views import HealthCheckView, AsyncHealthCheckView

urlpatterns = [
    path("health/", HealthCheckView.as_view()),         # WSGI
    path("ahealth/", AsyncHealthCheckView.as_view()),   # ASGI
]
```

Each view runs every registered ping and returns:

- `200 {"healthy": [...], "failing": {}}` on full success.
- `503 {"healthy": [...], "failing": {"<service>": "<exc repr>"}}` if any
  ping raises.

Register pings on factories:

```python
django_svcs.register_factory(
    Database, build_database, ping=lambda db: db.execute("SELECT 1"),
)
```

## Testing

Two patterns, depending on scope:

### Per-request override (one test)

```python
from django.test import RequestFactory
import django_svcs

def test_one():
    request = RequestFactory().get("/")
    django_svcs.overwrite_factory(request, PaymentClient, FakePayment)
    # call view code with this request — uses FakePayment
```

### Registry-scope override (whole test class via test client)

```python
class CheckoutFailureTests(TestCase):
    def setUp(self):
        reg = django_svcs.get_registry()
        self._original = reg._services.pop(PaymentClient)
        django_svcs.register_factory(PaymentClient, FailingPayment)

    def tearDown(self):
        reg = django_svcs.get_registry()
        reg._services.pop(PaymentClient, None)
        reg._services[PaymentClient] = self._original
```

## Streaming responses

`StreamingHttpResponse` is the one place naïve middleware breaks: the view
returns immediately, but Django consumes the body iterator **after**
middleware finishes. If `SvcsMiddleware` closed the container the moment
the view returned, any service the iterator depends on (DB cursor, HTTP
client, file handle) would already be gone — silent corruption.

`SvcsMiddleware` wraps `streaming_content` in a generator that runs
container cleanup in `finally`, so cleanup fires after the last byte is
yielded.

```python
from django.http import StreamingHttpResponse
from django.views.decorators.http import require_GET

import django_svcs


@require_GET
def export_csv(request):
    svc = django_svcs.get(request, ReportService)

    def rows():
        yield "id,total\n"
        for dto in svc.stream_rows():     # backed by a live DB cursor
            yield f"{dto.id},{dto.total}\n"

    return StreamingHttpResponse(rows(), content_type="text/csv")
```

Same wrapper covers async streaming and `FileResponse`.

## ASGI registry shutdown

The AppConfig registers `atexit` to close the sync registry on graceful
interpreter shutdown. ASGI deployments need a lifespan hook so async
`on_registry_close` callbacks can run:

```python
# asgi.py
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django_app = get_asgi_application()


async def application(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                import django_svcs
                await django_svcs.aclose_registry()
                await send({"type": "lifespan.shutdown.complete"})
                return
    else:
        await django_app(scope, receive, send)
```

## What it does in one paragraph

`DjangoSvcsConfig.ready()` creates a process-wide `svcs.Registry` (the recipe
book). On each request, `SvcsMiddleware` is a thin teardown guard: it does
not create the container itself — that happens lazily inside
`svcs_from(request)` the first time a view asks for a service. After the
response (or after streaming-body iteration completes), the middleware
closes the container, running every registered cleanup hook. Sync and async
views are both supported via Django's standard hybrid middleware pattern.

## Relationship to upstream `svcs`

This package depends on [`svcs`](https://github.com/hynek/svcs) and
re-exports its core types (`Registry`, `Container`, `ServicePing`) where
useful. The svcs concepts (registry, container, factories, pings,
`enter=True/False`) are unchanged — `django-svcs` only provides the Django
glue: the `AppConfig`, the middleware, the request-bound helpers, the
per-request `bind_local_*` shortcuts, the `factory` adapter, and the
healthcheck CBVs.

If you're new to svcs, read its [docs](https://svcs.hynek.me) first;
everything there carries over.

## License

MIT
