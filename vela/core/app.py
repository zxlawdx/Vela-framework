"""
vela.core.app
Classe principal do framework Vela.
Responsável por montar a aplicação, registrar apps, rotas e a janela.
"""

import os
import importlib
from vela.core.router import Router
from vela.core.window import DesktopWindow
from vela.core.bridge import BaseBridge
from vela.log.logger import VelaLogger


class VelaApp:
    def __init__(self, settings_module="config.settings"):
        self.logger = VelaLogger("VelaApp")
        self.router = Router()
        self.bridge = BaseBridge(router=self.router)
        self._apps = []
        self._settings = self._load_settings(settings_module)
        self.logger.info(f"Vela iniciado | settings: {settings_module}")

    def _load_settings(self, module_path: str):
        """Carrega o módulo de configurações dinamicamente."""
        try:
            settings = importlib.import_module(module_path)
            self.logger.info("Settings carregadas com sucesso.")
            return settings
        except ModuleNotFoundError:
            self.logger.error(f"Settings '{module_path}' não encontradas.")
            raise

    def register_app(self, app_module: str):
        """
        Registra um app (similar ao INSTALLED_APPS do Django).
        Espera que o app tenha um views/__init__.py que importe as views.

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
            self._apps.append(app_module)
        except ModuleNotFoundError as e:
            self.logger.error(f"Falha ao registrar app '{app_module}': {e}")
            raise

    def run(self):
        """Inicia a janela desktop."""
        settings = self._settings

        title = getattr(settings, "APP_TITLE", "Vela App")
        width = getattr(settings, "WINDOW_WIDTH", 1200)
        height = getattr(settings, "WINDOW_HEIGHT", 800)
        debug = getattr(settings, "DEBUG", True)
        entry_route = getattr(settings, "ENTRY_ROUTE", "/")

        self.logger.info(f"Iniciando janela: {title} ({width}x{height})")

        window = DesktopWindow(
            title=title,
            width=width,
            height=height,
            bridge=self.bridge,
            debug=debug,
            entry_route=entry_route,
        )
        window.run()
