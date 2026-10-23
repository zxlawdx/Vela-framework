# SPDX-License-Identifier: MPL-2.0
"""Routing visual do Vela."""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from html import escape
from typing import Any, Callable
from uuid import uuid4

from vela.exceptions import ConfigurationError
from vela.log.logger import VelaLogger


@dataclass(slots=True)
class Route:
    path: str
    handler: Callable[[dict[str, Any]], str]
    title: str = ""
    icon: str = ""
    group: str = ""
    order: int = 0
    layout: str = "default"
    theme: str | None = None
    show_in_sidebar: bool = True
    name: str = ""

    def render(
        self,
        params: dict[str, Any] | None = None,
        router: "Router | None" = None,
    ) -> str:
        context = dict(params or {})
        context["router"] = router
        if router and router.base_url:
            context["__base_url__"] = router.base_url
        return self.handler(context)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "title": self.title,
            "icon": self.icon,
            "group": self.group,
            "order": self.order,
            "layout": self.layout,
            "theme": self.theme,
            "show_in_sidebar": self.show_in_sidebar,
        }


@dataclass(frozen=True, slots=True)
class RouteResult(Mapping[str, Any]):
    ok: bool
    html: str
    layout: str = "default"
    theme: str | None = None
    status: int = 200
    error_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "html": self.html,
            "layout": self.layout,
            "theme": self.theme,
            "status": self.status,
            "error_id": self.error_id,
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())

    def __len__(self) -> int:
        return 6

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)


class Router:
    """Registro O(1) médio por path e por nome."""

    def __init__(self):
        self._routes: dict[str, Route] = {}
        self._named: dict[str, Route] = {}
        self._sidebar_cache: tuple[dict[str, Any], ...] | None = None
        self.logger = VelaLogger("router")
        self.base_url: str | None = None
        self.debug = False

    @staticmethod
    def _validate_path(path: str) -> None:
        if not isinstance(path, str) or not path.startswith("/") or "\x00" in path:
            raise ConfigurationError("Route path deve ser uma string absoluta iniciada por '/'.")

    def add(
        self,
        path: str,
        handler: Callable[[dict[str, Any]], str],
        title: str = "",
        icon: str = "",
        group: str = "",
        order: int = 0,
        layout: str = "default",
        theme: str | None = None,
        show_in_sidebar: bool = True,
        name: str | None = None,
        *,
        replace: bool = False,
    ) -> Route:
        self._validate_path(path)
        if not callable(handler):
            raise ConfigurationError(f"Handler da rota {path!r} deve ser chamável.")
        if layout not in {"default", "blank"}:
            raise ConfigurationError("layout de rota deve ser 'default' ou 'blank'.")
        route_name = name or path.lstrip("/") or "index"
        existing = self._routes.get(path)
        logical_same_handler = bool(
            existing
            and getattr(existing.handler, "__module__", None)
            == getattr(handler, "__module__", None)
            and getattr(existing.handler, "__name__", None)
            == getattr(handler, "__name__", None)
            and existing.name == route_name
        )
        if existing and not (replace or logical_same_handler):
            raise ConfigurationError(f"Rota duplicada para path {path!r}.")
        named = self._named.get(route_name)
        if named and named.path != path:
            raise ConfigurationError(
                f"Nome de rota duplicado {route_name!r}: {named.path!r} e {path!r}."
            )

        route = Route(
            path=path,
            handler=handler,
            title=title,
            icon=icon,
            group=group,
            order=int(order),
            layout=layout,
            theme=theme,
            show_in_sidebar=bool(show_in_sidebar),
            name=route_name,
        )
        if existing and existing.name != route_name:
            self._named.pop(existing.name, None)
        self._routes[path] = route
        self._named[route_name] = route
        self._sidebar_cache = None
        self.logger.info(
            f"Rota registrada: {path} → {getattr(handler, '__name__', type(handler).__name__)} "
            f"[name={route_name}, layout={layout}]"
        )
        return route

    def resolve(self, path: str, params: dict[str, Any] | None = None) -> RouteResult:
        route = self._routes.get(path)
        if route is None:
            self.logger.warning(f"Rota não encontrada: {path}")
            return RouteResult(ok=False, html=self._not_found(path), status=404)
        try:
            html = route.render(params, router=self)
        except Exception as exc:
            error_id = self._error_id()
            self.logger.exception(f"{error_id} erro ao renderizar {path}: {exc}")
            return RouteResult(
                ok=False,
                html=self._render_error(path, exc, error_id),
                layout=route.layout,
                theme=route.theme,
                status=500,
                error_id=error_id,
            )
        return RouteResult(
            ok=True,
            html=str(html),
            layout=route.layout,
            theme=route.theme,
            status=200,
        )

    def url_for(self, name: str) -> str:
        route = self._named.get(name)
        if route is None:
            raise KeyError(f"Rota nomeada {name!r} não encontrada.")
        return route.path

    def get_sidebar_routes(self) -> list[dict[str, Any]]:
        if self._sidebar_cache is None:
            visible = (
                route
                for route in self._routes.values()
                if route.show_in_sidebar and route.title
            )
            self._sidebar_cache = tuple(
                route.to_dict() for route in sorted(visible, key=lambda route: route.order)
            )
        return [dict(route) for route in self._sidebar_cache]

    def list_routes(self) -> list[dict[str, Any]]:
        return [route.to_dict() for route in self._routes.values()]

    def refresh_module(self, module_name: str, module: Any) -> int:
        """Atualiza referências de handlers após reload seletivo de um módulo."""
        updated = 0
        for route in self._routes.values():
            handler = route.handler
            if getattr(handler, "__module__", None) != module_name:
                continue
            name = getattr(handler, "__name__", "")
            replacement = getattr(module, name, None)
            if callable(replacement):
                route.handler = replacement
                updated += 1
        return updated

    @staticmethod
    def _error_id() -> str:
        return "VELA-E-" + uuid4().hex[:8]

    def _not_found(self, path: str) -> str:
        safe_path = escape(str(path), quote=True)
        return f"""
        <div class="flex flex-col items-center justify-center h-full text-zinc-400">
            <h1 class="text-6xl font-black text-zinc-700">404</h1>
            <p class="mt-2 text-xl">Rota <code class="text-blue-400">{safe_path}</code> não encontrada.</p>
        </div>
        """

    def _render_error(self, path: str, error: Exception, error_id: str) -> str:
        safe_id = escape(error_id, quote=True)
        if self.debug:
            detail = f"{escape(str(path), quote=True)}: {escape(str(error), quote=True)}"
            return f"""
            <div class="flex flex-col items-center justify-center h-full text-red-400 p-8">
                <h1 class="text-4xl font-black text-red-600 mb-4">Erro na view</h1>
                <p class="font-mono text-sm bg-zinc-900 p-4 rounded-xl">{detail}</p>
                <p class="mt-2 text-xs">Código: {safe_id}</p>
            </div>
            """
        return f"""
        <div class="flex flex-col items-center justify-center h-full text-red-400 p-8">
            <h1 class="text-4xl font-black text-red-600 mb-4">Erro interno.</h1>
            <p class="font-mono text-sm">Código: {safe_id}</p>
        </div>
        """
