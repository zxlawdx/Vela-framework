# SPDX-License-Identifier: MPL-2.0
"""Facade compatível de API com registry por aplicação."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Iterator

from vela.core.api_router import ApiRouter


class ApiFacade:
    def __init__(self):
        self._blueprint = ApiRouter()
        self._current: ContextVar[ApiRouter | None] = ContextVar("vela_api_router", default=None)

    def _target(self) -> ApiRouter:
        return self._current.get() or self._blueprint

    @property
    def routes(self):
        return self._target().routes

    def new_router(self) -> ApiRouter:
        return self._blueprint.clone()

    @contextmanager
    def bind(self, router: ApiRouter) -> Iterator[ApiRouter]:
        token = self._current.set(router)
        try:
            yield router
        finally:
            self._current.reset(token)

    def add_route(self, method: str, path: str, handler: Callable[..., Any]):
        """Register on the reusable blueprint and on the active app router.

        Consumer API modules are often imported for the first time while
        ``VelaApp.register_app`` has a router bound. Persisting that decorator in
        the blueprint makes a second VelaApp instance in the same process receive
        the same routes even though Python correctly reuses the cached module.
        """
        blueprint_route = self._blueprint.add_route(method, path, handler)
        current = self._current.get()
        if current is not None and current is not self._blueprint:
            return current.add_route(method, path, handler)
        return blueprint_route

    def _decorator(self, method: str, path: str):
        def decorator(func: Callable[..., Any]):
            self.add_route(method, path, func)
            return func

        return decorator

    def get(self, path: str):
        return self._decorator("GET", path)

    def head(self, path: str):
        return self._decorator("HEAD", path)

    def post(self, path: str):
        return self._decorator("POST", path)

    def put(self, path: str):
        return self._decorator("PUT", path)

    def delete(self, path: str):
        return self._decorator("DELETE", path)

    def patch(self, path: str):
        return self._decorator("PATCH", path)

    def options(self, path: str):
        return self._decorator("OPTIONS", path)


api = ApiFacade()
__all__ = ["api", "ApiFacade"]
