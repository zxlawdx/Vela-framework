"""
vela.core.bridge
================
Ponte de comunicação entre Python e JavaScript via pywebview.

Evolução da arquitetura:
  - Recebe `config` com layout global { sidebar, topbar }
  - navigate() retorna { ok, html, layout, path }
  - get_config() expõe configuração global ao JS
  - get_routes() retorna apenas rotas visíveis na sidebar
  - url_for() permite que o JS resolva rotas nomeadas

Todas as funções públicas ficam disponíveis no JS como:
    window.pywebview.api.nome_da_funcao()
"""

import json
import sys
import importlib
from vela.log.logger import VelaLogger


class BaseBridge:
    """
    Bridge base do Vela.

    Parâmetros:
        router   Instância de Router (obrigatório)
        config   Dicionário de configuração global do app.
                 Estrutura padrão:
                 {
                   "title": "Meu App",
                   "layout": {
                       "sidebar": True,
                       "topbar": True
                   }
                 }

    Herança:
        Crie sua própria Bridge herdando desta classe para
        adicionar métodos específicos do seu app.

        class MyBridge(BaseBridge):
            def get_user(self):
                return { "name": "Dev" }
    """

    def __init__(self, router=None, config: dict = None):
        self.router = router
        self.logger = VelaLogger("Bridge")

        # Config padrão — o dev pode sobrescrever via VelaApp(config={...})
        self.config = config or {
            "title": "Vela App",
            "layout": {
                "sidebar": True,
                "topbar": True,
            },
        }

    # ─── Configuração ─────────────────────────────────────────────────────

    def get_config(self) -> dict:
        """
        Retorna a configuração global do app para o shell JS.
        Chamado automaticamente em Vela.init().

        JS:
            const config = await window.pywebview.api.get_config()
            // config.layout.sidebar → true/false
            // config.layout.topbar  → true/false
            // config.title          → "Meu App"
        """
        return self.config

    # ─── Navegação ────────────────────────────────────────────────────────

    def navigate(self, path: str, params: str = "{}") -> dict:
        """
        Navega para uma rota e retorna o HTML + metadata da página.

        Retorno:
            {
                "ok": True,
                "html": "<div>...</div>",
                "layout": "default",   # ou "blank"
                "path": "/dashboard"
            }

        JS:
            const result = await window.pywebview.api.navigate("/dashboard")
            if (result.ok) {
                page.innerHTML = result.html
                Vela.applyRouteLayout(result.layout)
            }
        """
        # Hot reload dos módulos da aplicação (não do framework)
        self._reload_app_modules()

        try:
            parsed_params = json.loads(params)
        except (json.JSONDecodeError, TypeError):
            parsed_params = {}

        result = self.router.resolve(path, parsed_params)

        self.logger.info(
            f"navigate() → {path} [layout={result.get('layout', 'default')}]"
        )

        return {
            "ok": True,
            "html": result["html"],
            "layout": result["layout"],
            "path": path,
        }

    # ─── Rotas ────────────────────────────────────────────────────────────

    def get_routes(self) -> list:
        """
        Retorna rotas visíveis na sidebar, ordenadas por order.

        JS:
            const routes = await window.pywebview.api.get_routes()
            // routes = [{ path, name, title, icon, group, order, layout, show_in_sidebar }]
        """
        return self.router.get_sidebar_routes()

    def url_for(self, name: str) -> dict:
        """
        Resolve o path de uma rota pelo nome.

        JS:
            const { path } = await window.pywebview.api.url_for("dashboard")
            Vela.navigate(path)
        """
        try:
            path = self.router.url_for(name)
            return {"ok": True, "path": path}
        except KeyError as e:
            self.logger.warning(str(e))
            return {"ok": False, "path": None, "error": str(e)}

    # ─── Sistema ──────────────────────────────────────────────────────────

    def ping(self) -> str:
        """Health check simples para testar a bridge."""
        return "pong"

    def get_framework_info(self) -> dict:
        """Retorna informações do framework."""
        import vela
        return {
            "name": "Vela Framework",
            "version": vela.__version__,
        }

    def log(self, level: str, message: str):
        """
        Permite que o JS escreva nos logs do Python.

        JS:
            window.pywebview.api.log("info", "Página carregada")
        """
        level = level.lower()
        if level == "info":
            self.logger.info(f"[JS] {message}")
        elif level == "warning":
            self.logger.warning(f"[JS] {message}")
        elif level == "error":
            self.logger.error(f"[JS] {message}")

    # ─── Internal ─────────────────────────────────────────────────────────

    def _reload_app_modules(self):
        """
        Recarrega módulos da aplicação (prefixo 'apps.')
        para permitir hot reload em desenvolvimento.
        """
        modules_to_reload = [
            name for name in list(sys.modules.keys())
            if name.startswith("apps.")
        ]
        for name in modules_to_reload:
            try:
                importlib.reload(sys.modules[name])
            except Exception as e:
                self.logger.warning(f"Não foi possível recarregar {name}: {e}")
