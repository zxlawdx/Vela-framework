"""
vela.core.router
Sistema de rotas do framework Vela.
Mapeia caminhos (ex: "/dashboard") para funções Python que retornam HTML.
"""

from vela.log.logger import VelaLogger
import importlib
import sys

       
class Route:
    def __init__(self, path, handler, title):
        self.path = path
        self.title = title
        self._module_name = handler.__module__  
        self._func_name = handler.__name__       

    def render(self, params: dict = None) -> str:

        # sempre reimporta o módulo do disco antes de chamar
        module = importlib.import_module(self._module_name)
        importlib.reload(module)
        handler = getattr(module, self._func_name)
        return handler(params or {})
        


class Router:
    def __init__(self):
        self._routes: dict[str, Route] = {}
        self.logger = VelaLogger("Router")

    def add(self, path: str, handler, title: str = ""):
        """
        Registra uma rota.

        Exemplo:
            router.add("/dashboard", dashboard_view, title="Dashboard")
        """
        self._routes[path] = Route(path, handler, title)
        self.logger.info(f"Rota registrada: {path} → {handler.__name__}")

    def resolve(self, path: str, params: dict = None) -> str:
        """
        Resolve um caminho e retorna o HTML renderizado.
        Retorna página 404 se não encontrada.
        """
        route = self._routes.get(path)
        if not route:
            self.logger.warning(f"Rota não encontrada: {path}")
            return self._not_found(path)

        self.logger.info(f"Navegando para: {path}")
        return route.render(params)

    def list_routes(self) -> list[dict]:
        """Retorna lista de rotas registradas (para debug/shell)."""
        return [
            {"path": r.path, "handler": r._func_name, "title": r.title}
            for r in self._routes.values()
        ]

    def _not_found(self, path: str) -> str:
        return f"""
        <div class="flex flex-col items-center justify-center h-full text-zinc-400">
            <h1 class="text-6xl font-black text-zinc-700">404</h1>
            <p class="mt-2 text-xl">Rota <code class="text-blue-400">{path}</code> não encontrada.</p>
        </div>
        """
