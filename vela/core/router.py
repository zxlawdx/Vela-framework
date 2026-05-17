"""
vela.core.router
================
Sistema de rotas do framework Vela.

Evolução da arquitetura:
  - Suporte a icon, group, order, layout, show_in_sidebar, name
  - resolve() retorna dict com { html, layout } em vez de string pura
  - Rotas nomeadas com url_for(name) para navegação estilo Django
  - Hot reload via importlib.reload() em modo dev
"""

import importlib
import sys
from vela.log.logger import VelaLogger


# ─── Route ────────────────────────────────────────────────────────────────────

class Route:
    """
    Representa uma rota registrada no Vela.

    Parâmetros:
        path            URL da rota, ex: "/dashboard"
        handler         Função Python que retorna HTML (str)
        title           Título exibido na sidebar e topbar
        icon            Emoji ou ícone (ex: "📊", "⚙️")
        group           Grupo da sidebar para agrupar rotas futuramente
        order           Ordem de exibição na sidebar (menor = primeiro)
        layout          "default" usa sidebar+topbar; "blank" esconde tudo
        show_in_sidebar Se False, a rota não aparece na sidebar
        name            Nome único para navegação estilo Django.
                        Padrão: o próprio path sem a barra inicial.
    """

    def __init__(
        self,
        path: str,
        handler,
        title: str = "",
        icon: str = "",
        group: str = "",
        order: int = 0,
        layout: str = "default",
        show_in_sidebar: bool = True,
        name: str = None,
    ):
        self.path = path
        self.title = title
        self.icon = icon
        self.group = group
        self.order = order
        self.layout = layout
        self.show_in_sidebar = show_in_sidebar

        # Nome para url_for(): padrão é o path sem "/" inicial
        self.name = name or path.lstrip("/") or "index"

        # Guardamos referência por módulo+função para hot reload funcionar
        self._module_name = handler.__module__
        self._func_name = handler.__name__

    def render(self, params: dict = None, router=None) -> str:
        module = importlib.import_module(self._module_name)
        importlib.reload(module)
        handler = getattr(module, self._func_name)

        context = params or {}
        context["router"] = router

        return handler(context)

    def to_dict(self) -> dict:
        """Serializa a rota para envio ao frontend."""
        return {
            "path": self.path,
            "name": self.name,
            "title": self.title,
            "icon": self.icon,
            "group": self.group,
            "order": self.order,
            "layout": self.layout,
            "show_in_sidebar": self.show_in_sidebar,
        }


# ─── Router ───────────────────────────────────────────────────────────────────

class Router:
    """
    Registro central de rotas do Vela.

    Exemplo de uso:
        router.add("/dashboard", dashboard_view,
                   name="dashboard", title="Dashboard",
                   icon="📊", layout="default", show_in_sidebar=True)

        router.add("/login", login_view,
                   name="login", title="Login",
                   layout="blank", show_in_sidebar=False)
    """

    def __init__(self):
        # Índice por path: { "/dashboard": Route }
        self._routes: dict[str, Route] = {}
        # Índice por nome: { "dashboard": Route } — para url_for()
        self._named: dict[str, Route] = {}
        self.logger = VelaLogger("Router")

    # ─── Registro ────────────────────────────────────────────────────────

    def add(
        self,
        path: str,
        handler,
        title: str = "",
        icon: str = "",
        group: str = "",
        order: int = 0,
        layout: str = "default",
        show_in_sidebar: bool = True,
        name: str = None,
    ):
        """
        Registra uma rota no router.

        Exemplo:
            router.add("/filmes", filmes_view,
                       name="filmes", title="Filmes", icon="🎬")
        """
        route = Route(
            path=path,
            handler=handler,
            title=title,
            icon=icon,
            group=group,
            order=order,
            layout=layout,
            show_in_sidebar=show_in_sidebar,
            name=name,
        )

        self._routes[path] = route
        self._named[route.name] = route

        self.logger.info(
            f"Rota registrada: {path} → {handler.__name__} "
            f"[name={route.name}, layout={layout}]"
        )

    # ─── Resolução ────────────────────────────────────────────────────────

    def resolve(self, path: str, params: dict = None) -> dict:
        """
        Resolve um path e retorna um dict com html e layout.

        Retorno:
            {
                "html": "<div>...</div>",
                "layout": "default"   # ou "blank"
            }
        """
        route = self._routes.get(path)

        if not route:
            self.logger.warning(f"Rota não encontrada: {path}")
            return {
                "html": self._not_found(path),
                "layout": "default",
            }

        self.logger.info(f"Navegando para: {path} [layout={route.layout}]")

        try:
            html = route.render(params, router=self)
        except Exception as e:
            self.logger.error(f"Erro ao renderizar {path}: {e}")
            html = self._render_error(path, e)

        return {
            "html": html,
            "layout": route.layout,
        }

    # ─── URL nomeada (estilo Django) ──────────────────────────────────────

    def url_for(self, name: str) -> str:
        """
        Retorna o path de uma rota pelo nome.

        Exemplo:
            router.url_for("dashboard")  →  "/dashboard"

        Lança KeyError se o nome não existir.
        """
        route = self._named.get(name)
        if not route:
            raise KeyError(f"Rota nomeada '{name}' não encontrada.")
        return route.path

    # ─── Listagem ─────────────────────────────────────────────────────────

    def get_sidebar_routes(self) -> list[dict]:
        """
        Retorna rotas visíveis na sidebar, ordenadas por `order`.
        Usado pelo shell.html via bridge.get_routes().
        """
        visible = [
            r for r in self._routes.values()
            if r.show_in_sidebar and r.title
        ]
        return [r.to_dict() for r in sorted(visible, key=lambda r: r.order)]

    def list_routes(self) -> list[dict]:
        """Retorna todas as rotas (para debug/CLI)."""
        return [r.to_dict() for r in self._routes.values()]

    # ─── Páginas de erro internas ─────────────────────────────────────────

    def _not_found(self, path: str) -> str:
        return f"""
        <div class="flex flex-col items-center justify-center h-full text-zinc-400">
            <h1 class="text-6xl font-black text-zinc-700">404</h1>
            <p class="mt-2 text-xl">Rota <code class="text-blue-400">{path}</code> não encontrada.</p>
        </div>
        """

    def _render_error(self, path: str, error: Exception) -> str:
        return f"""
        <div class="flex flex-col items-center justify-center h-full text-red-400 p-8">
            <h1 class="text-4xl font-black text-red-600 mb-4">Erro na view</h1>
            <p class="font-mono text-sm bg-zinc-900 p-4 rounded-xl">{path}: {error}</p>
        </div>
        """
