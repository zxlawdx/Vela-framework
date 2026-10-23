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
        return self._target().add_route(method, path, handler)

    def get(self, path: str): return self._target().get(path)
    def head(self, path: str): return self._target().head(path)
    def post(self, path: str): return self._target().post(path)
    def put(self, path: str): return self._target().put(path)
    def delete(self, path: str): return self._target().delete(path)
    def patch(self, path: str): return self._target().patch(path)
    def options(self, path: str): return self._target().options(path)


api = ApiFacade()
__all__ = ["api", "ApiFacade"]
