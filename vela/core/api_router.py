# SPDX-License-Identifier: MPL-2.0
"""Registro de rotas HTTP com lookup/registro O(1) médio."""

from __future__ import annotations

import inspect
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Callable, get_type_hints

from vela.exceptions import ConfigurationError
from vela.log.logger import VelaLogger


@dataclass(slots=True)
class ApiRoute(Mapping[str, Any]):
    method: str
    path: str
    handler: Callable[..., Any]
    signature: inspect.Signature = field(init=False, repr=False)
    type_hints: dict[str, Any] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.signature = inspect.signature(self.handler)
        try:
            self.type_hints = get_type_hints(self.handler)
        except (NameError, TypeError):
            self.type_hints = {}

    def __getitem__(self, key: str) -> Any:
        if key in {"method", "path", "handler", "signature"}:
            return getattr(self, key)
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(("method", "path", "handler"))

    def __len__(self) -> int:
        return 3


class ApiRouter:
    def __init__(self):
        self._routes: dict[tuple[str, str], ApiRoute] = {}
        self.logger = VelaLogger("api.router")

    @property
    def routes(self) -> list[ApiRoute]:
        return list(self._routes.values())

    def add_route(self, method: str, path: str, handler: Callable[..., Any]) -> ApiRoute:
        method = str(method).upper()
        if method not in {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"}:
            raise ConfigurationError(f"Método HTTP não suportado: {method!r}.")
        if not isinstance(path, str) or not path.startswith("/") or "\x00" in path:
            raise ConfigurationError("API path deve iniciar por '/'.")
        if not callable(handler):
            raise ConfigurationError("Handler de API deve ser chamável.")
        route = ApiRoute(method=method, path=path, handler=handler)
        self._routes[(method, path)] = route
        return route

    def get_route(self, method: str, path: str) -> ApiRoute | None:
        return self._routes.get((method.upper(), path))

    def clone(self) -> "ApiRouter":
        other = ApiRouter()
        for route in self._routes.values():
            other.add_route(route.method, route.path, route.handler)
        return other

    def refresh_module(self, module_name: str, module: Any) -> int:
        updated = 0
        for key, route in tuple(self._routes.items()):
            if getattr(route.handler, "__module__", None) != module_name:
                continue
            name = getattr(route.handler, "__name__", "")
            replacement = getattr(module, name, None)
            if callable(replacement):
                self._routes[key] = ApiRoute(route.method, route.path, replacement)
                updated += 1
        return updated

    def _decorator(self, method: str, path: str):
        def decorator(func: Callable[..., Any]):
            self.add_route(method, path, func)
            return func

        return decorator

    def get(self, path: str):
        return self._decorator("GET", path)

    def post(self, path: str):
        return self._decorator("POST", path)

    def put(self, path: str):
        return self._decorator("PUT", path)

    def delete(self, path: str):
        return self._decorator("DELETE", path)

    def patch(self, path: str):
        return self._decorator("PATCH", path)
