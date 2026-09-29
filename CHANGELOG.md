# Changelog

## 0.2.0

### Added

- `suppress_context_exit` on `register_factory`, `register_value`,
  `overwrite_factory`, and `overwrite_value`. The default remains `True`.
  Setting it to `False` lets service cleanup inspect exceptions observed by
  `SvcsMiddleware`, including view failures, streaming failures, and async
  cancellation.
- Documentation and regression tests for using upstream `svcs.autowire()`
  and `svcs.aautowire()` with the existing Django registration helpers.
- Regression tests for request-local healthchecks and exception-aware
  cleanup, plus a dedicated Protocol typing check.
- Mypy 2.2+ and Django type stubs for development type checks of the package
  and public API examples, including sync and async middleware return types.

### Changed

- **Breaking:** raised the minimum Python version to 3.12 and the minimum
  Django version to 5.2. Django remains capped below 6.0.
- Target Python 3.12 compatibility in Mypy and Ruff; development uses Python 3.13.
- Raised the minimum `svcs` version from `25.1.0` to `26.2.0` and updated
  the lockfile. Added a direct dependency on `typing-extensions>=4.13.0`.
- Registration and resolution helpers now use `TypeForm` annotations.
  `get()` and `aget()` infer return types for Protocols and abstract types.
- Healthchecks inherit upstream's new container-local behavior: local
  pings are included, local registrations override global pings, and a
  local registration without a ping disables the global ping for that
  service type.

### Fixed

- Middleware return annotations distinguish synchronous responses from
  coroutine wrappers, including callbacks that return a `Future`.
- Async streaming responses returned through synchronous middleware retain
  their async iterator and close their service container after consumption.

### Deprecated

- `get_abstract()` and `aget_abstract()`: use `get()` and `aget()` instead.
  Both compatibility helpers remain available without deprecation warnings.

### Upgrading from 0.1.0

- Upgrade to Python 3.12+ and Django 5.2 (`>=5.2,<6.0`) before installing
  0.2.0. Python 3.10/3.11 and Django 4.2/5.0/5.1 are no longer supported.
- Update dependency pins and lockfiles to allow `svcs>=26.2.0`.
- Review healthchecks if you use request-local bindings. A failing local
  ping that was previously ignored can now produce a 503 response; a local
  binding without a ping can remove a previously failing global check.
- Existing calls and default cleanup behavior are preserved. If you already
  set `suppress_context_exit=False` directly on the raw registry, cleanup
  now receives exceptions observed by the middleware.
- Exception forwarding depends on Django middleware ordering. Exceptions
  consumed by another handler before `SvcsMiddleware` observes them cannot
  be forwarded. See [exception-aware cleanup](README.md#exception-aware-cleanup).
- Use a type checker with `TypeForm` support. Mypy 2.2+ enables it by
  default; older versions that support it need
  `--enable-incomplete-feature=TypeForm`.

## 0.1.0

- Initial Django integration for `svcs`, with a process-wide registry and
  lazy request-scoped containers.
- Sync and async service resolution, streaming response cleanup,
  request-local bindings, test overrides, and healthcheck views.
