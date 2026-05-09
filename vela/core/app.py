"""
vela.core.app
=============
Classe principal do framework Vela.

Evolução da arquitetura:
  - VelaApp aceita `title` e `layout` como parâmetros diretos
  - Config global propagada para a Bridge
  - Mantém compatibilidade com settings_module legado

Exemplo de uso:
    app = VelaApp(
        title="Meu App",
        layout={
            "sidebar": True,
            "topbar": True,
        }
    )
    app.register_app("apps.home")
    app.run()

Ou via settings (legado):
    app = VelaApp(settings_module="config.settings")
"""

import os
import importlib
from vela.core.router import Router
from vela.core.window import DesktopWindow
from vela.core.bridge import BaseBridge
from vela.log.logger import VelaLogger


class VelaApp:
    """
    Ponto de entrada principal do framework Vela.

    Parâmetros:
        title           Título da janela (override do settings)
        layout          Dict { sidebar: bool, topbar: bool }
        settings_module Módulo de configurações (ex: "config.settings")
        bridge_class    Classe de bridge customizada (deve herdar BaseBridge)
    """

    def __init__(
        self,
        title: str = None,
        layout: dict = None,
        settings_module: str = "config.settings",
        bridge_class=None,
    ):
        self.logger = VelaLogger("VelaApp")
        self.router = Router()

        # Carrega settings (tolerante — não quebra se não existir)
        self._settings = self._load_settings(settings_module)

        # Monta a config global, mesclando settings + parâmetros diretos
        self._config = self._build_config(title=title, layout=layout)

        # Instancia a bridge com a config
        bridge_cls = bridge_class or BaseBridge
        self.bridge = bridge_cls(
            router=self.router,
            config=self._config,
        )

        self.logger.info(
            f"Vela iniciado | title={self._config['title']} "
            f"| sidebar={self._config['layout']['sidebar']} "
            f"| topbar={self._config['layout']['topbar']}"
        )

    # ─── Boot ────────────────────────────────────────────────────────────

    def _load_settings(self, module_path: str):
        """Carrega o módulo de configurações dinamicamente."""
        try:
            settings = importlib.import_module(module_path)
            self.logger.info(f"Settings carregadas: {module_path}")
            return settings
        except ModuleNotFoundError:
            self.logger.warning(
                f"Settings '{module_path}' não encontradas — usando defaults."
            )
            return None

    def _build_config(self, title: str = None, layout: dict = None) -> dict:
        """
        Monta a config global mesclando defaults, settings e parâmetros diretos.
        Parâmetros diretos têm prioridade sobre settings.
        """
        s = self._settings

        # Defaults
        config = {
            "title": "Vela App",
            "layout": {
                "sidebar": True,
                "topbar": True,
            },
            "entry_route": "/",
            "window": {
                "width": 1280,
                "height": 800,
            },
            "debug": True,
        }

        # Override com settings (se existir)
        if s:
            if hasattr(s, "APP_TITLE"):
                config["title"] = s.APP_TITLE
            if hasattr(s, "ENTRY_ROUTE"):
                config["entry_route"] = s.ENTRY_ROUTE
            if hasattr(s, "WINDOW_WIDTH"):
                config["window"]["width"] = s.WINDOW_WIDTH
            if hasattr(s, "WINDOW_HEIGHT"):
                config["window"]["height"] = s.WINDOW_HEIGHT
            if hasattr(s, "DEBUG"):
                config["debug"] = s.DEBUG
            # Suporte a LAYOUT no settings
            if hasattr(s, "LAYOUT"):
                config["layout"].update(s.LAYOUT)

        # Override com parâmetros diretos (maior prioridade)
        if title:
            config["title"] = title
        if layout:
            config["layout"].update(layout)

        return config

    # ─── Apps ────────────────────────────────────────────────────────────

    def register_app(self, app_module: str):
        """
        Registra um app no framework.

        O app deve ter um views/__init__.py com a função:
            def register_routes(router): ...

        Exemplo:
            app.register_app("apps.home")
        """
        try:
            views_module = importlib.import_module(f"{app_module}.views")
            if hasattr(views_module, "register_routes"):
                views_module.register_routes(self.router)
                self.logger.info(f"App '{app_module}' registrado.")
            else:
                self.logger.warning(
                    f"App '{app_module}' não tem register_routes() em views/__init__.py"
                )
        except ModuleNotFoundError as e:
            self.logger.error(f"Falha ao registrar app '{app_module}': {e}")
            raise

    # ─── Run ─────────────────────────────────────────────────────────────

    def run(self):
        """Inicia a janela desktop."""
        c = self._config

        self.logger.info(
            f"Iniciando janela: {c['title']} "
            f"({c['window']['width']}x{c['window']['height']})"
        )

        window = DesktopWindow(
            title=c["title"],
            width=c["window"]["width"],
            height=c["window"]["height"],
            bridge=self.bridge,
            debug=c["debug"],
            entry_route=c["entry_route"],
        )
        window.run()
