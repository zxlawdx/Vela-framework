"""
vela.core.bridge
Ponte de comunicação entre Python e JavaScript via pywebview.
Todas as funções públicas aqui ficam disponíveis no JS como:
    window.pywebview.api.nome_da_funcao()
"""

import json
from vela.log.logger import VelaLogger
import sys
import importlib

class BaseBridge:
    """
    Bridge base do Vela.
    Gerencie chamadas Python↔JS e roteamento de páginas.
    Você pode herdar desta classe para adicionar métodos do seu app.
    """

    def __init__(self, router=None):
        self.router = router
        self.logger = VelaLogger("Bridge")

    # ─── Navegação ──────────────────────────────────────────────────────────

    def navigate(self, path: str, params: str = "{}") -> dict:
        """
        Navega para uma rota e retorna o HTML da página.
        Chamado pelo JS quando o usuário clica num link interno.

        JS:
            const result = await window.pywebview.api.navigate("/dashboard");
            document.getElementById("page").innerHTML = result.html;
        """
        self.reload_app_modules()

        try:
            parsed_params = json.loads(params)
        except Exception:
            parsed_params = {}

        html = self.router.resolve(path, parsed_params)
        self.logger.info(f"navigate() → {path}")
        return {"ok": True, "html": html, "path": path}
    
    def reload_app_modules(self):
        ##força o framework ler os módulos ao recarregar o app
        modulos_para_carregar = [
            name for name in sys.modules
            if name.startswith("apps.")
        ]
        for name in modulos_para_carregar:
            try:
                importlib.reload(sys.modules[name])
            except Exception as e:
                self.logger.warning(f"Não foi possível recarregar {nome}: {e}")
                
    def get_routes(self) -> list:
        """Retorna todas as rotas registradas (útil para sidebar dinâmica)."""
        return self.router.list_routes()

    # ─── Sistema ─────────────────────────────────────────────────────────────

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
        """Permite que o JS escreva nos logs do Python."""
        level = level.lower()
        if level == "info":
            self.logger.info(f"[JS] {message}")
        elif level == "warning":
            self.logger.warning(f"[JS] {message}")
        elif level == "error":
            self.logger.error(f"[JS] {message}")
