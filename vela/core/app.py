"""
vela.core.app
=============
Classe principal do framework Vela.
"""

import importlib

from vela.api import api
from vela.core.api_server import ApiServer
from vela.core.router import Router
from vela.core.window import DesktopWindow
from vela.core.bridge import BaseBridge
from vela.log.logger import VelaLogger


class VelaApp:
    """
    Ponto de entrada principal do framework Vela.
    """

    def __init__(
        self,
        title: str = None,
        layout: dict = None,
        settings_module: str = "config.settings",
        bridge_class=None,
        enable_api: bool = True,
    ):
        self.logger = VelaLogger("VelaApp")
        self.router = Router()
        self.enable_api = enable_api

        self._settings = self._load_settings(settings_module)
        self._config = self._build_config(title=title, layout=layout)

        bridge_cls = bridge_class or BaseBridge
        self.bridge = bridge_cls(
            router=self.router,
            config=self._config,
        )

        self.api_server = None

        self.logger.info(
            f"Vela iniciado | title={self._config['title']} "
            f"| sidebar={self._config['layout']['sidebar']} "
            f"| topbar={self._config['layout']['topbar']} "
            f"| api={self._config['api']['enabled']}"
        )

    # ─── Settings ────────────────────────────────────────────────────────

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
        """
        s = self._settings

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

            "api": {
                "enabled": self.enable_api,
                "host": "127.0.0.1",
                "port": 8000,
            },
        }

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

            if hasattr(s, "LAYOUT"):
                config["layout"].update(s.LAYOUT)

            if hasattr(s, "API"):
                config["api"].update(s.API)

        if title:
            config["title"] = title

        if layout:
            config["layout"].update(layout)

        return config

    # ─── Apps ────────────────────────────────────────────────────────────

    def register_app(self, app_module: str):
        """
        Registra um app no framework.

        Suporta:
        - views.py
        - views/__init__.py
        - urls.py estilo Django
        - api.py com decorators @api.get, @api.post
        """

        # ─── Carrega rotas de tela ───────────────────────────────────────────

        try:
            views_module = importlib.import_module(f"{app_module}.views")

            if hasattr(views_module, "register_routes"):
                views_module.register_routes(self.router)
                self.logger.info(f"App '{app_module}' registrado.")
            else:
                self.logger.warning(
                    f"App '{app_module}' possui views, mas não tem register_routes()."
                )

        except ModuleNotFoundError:
            self.logger.info(f"App '{app_module}' não possui views.")

        # ─── Carrega urls.py estilo Django ───────────────────────────────────

        try:
            importlib.import_module(f"{app_module}.urls")
            self.logger.info(f"URLs do app '{app_module}' carregadas.")

        except ModuleNotFoundError as e:
            # Só ignora se o módulo urls.py do app realmente não existir.
            # Se o erro aconteceu dentro do urls.py, relança.
            if e.name == f"{app_module}.urls":
                self.logger.info(f"App '{app_module}' não possui urls.py.")
            else:
                self.logger.error(f"Erro ao carregar urls.py do app '{app_module}': {e}")
                raise

        # ─── Mantém suporte antigo a api.py com decorators ───────────────────

        try:
            importlib.import_module(f"{app_module}.api")
            self.logger.info(f"API do app '{app_module}' carregada.")

        except ModuleNotFoundError as e:
            if e.name == f"{app_module}.api":
                self.logger.info(f"App '{app_module}' não possui api.py.")
            else:
                self.logger.error(f"Erro ao carregar api.py do app '{app_module}': {e}")
                raise

    """
vela.core.app
=============
Classe principal do framework Vela.
"""

import importlib

from vela.api import api
from vela.core.api_server import ApiServer
from vela.core.router import Router
from vela.core.window import DesktopWindow
from vela.core.bridge import BaseBridge
from vela.log.logger import VelaLogger


class VelaApp:
    """
    Ponto de entrada principal do framework Vela.
    """

    def __init__(
        self,
        title: str = None,
        layout: dict = None,
        settings_module: str = "config.settings",
        bridge_class=None,
        enable_api: bool = True,
    ):
        self.logger = VelaLogger("VelaApp")
        self.router = Router()
        self.enable_api = enable_api

        self._settings = self._load_settings(settings_module)
        self._config = self._build_config(title=title, layout=layout)

        bridge_cls = bridge_class or BaseBridge
        self.bridge = bridge_cls(
            router=self.router,
            config=self._config,
        )

        self.api_server = None

        self.logger.info(
            f"Vela iniciado | title={self._config['title']} "
            f"| sidebar={self._config['layout']['sidebar']} "
            f"| topbar={self._config['layout']['topbar']} "
            f"| api={self._config['api']['enabled']}"
        )

    # ─── Settings ────────────────────────────────────────────────────────

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
        """
        s = self._settings

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

            "api": {
                "enabled": self.enable_api,
                "host": "127.0.0.1",
                "port": 8000,
            },
        }

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

            if hasattr(s, "LAYOUT"):
                config["layout"].update(s.LAYOUT)

            if hasattr(s, "API"):
                config["api"].update(s.API)

        if title:
            config["title"] = title

        if layout:
            config["layout"].update(layout)

        return config

    # ─── Apps ────────────────────────────────────────────────────────────

    def register_app(self, app_module: str):
        """
        Registra um app no framework.

        Suporta:
        - views.py ou views/__init__.py
        - urls.py estilo Django
        - api.py com decorators
        """

        # Carrega views
        try:
            views_module = importlib.import_module(f"{app_module}.views")

            if hasattr(views_module, "register_routes"):
                views_module.register_routes(self.router)
                self.logger.info(f"App '{app_module}' registrado.")
            else:
                self.logger.warning(
                    f"App '{app_module}' possui views, mas não tem register_routes()."
                )

        except ModuleNotFoundError:
            self.logger.info(f"App '{app_module}' não possui views.")

        # Carrega urls.py estilo Django
        try:
            importlib.import_module(f"{app_module}.urls")
            self.logger.info(f"URLs do app '{app_module}' carregadas.")

        except ModuleNotFoundError as e:
            if e.name == f"{app_module}.urls":
                self.logger.info(f"App '{app_module}' não possui urls.py.")
            else:
                self.logger.error(f"Erro ao carregar urls.py do app '{app_module}': {e}")
                raise

        # Carrega api.py com decorators
        try:
            importlib.import_module(f"{app_module}.api")
            self.logger.info(f"API do app '{app_module}' carregada.")

        except ModuleNotFoundError as e:
            if e.name == f"{app_module}.api":
                self.logger.info(f"App '{app_module}' não possui api.py.")
            else:
                self.logger.error(f"Erro ao carregar api.py do app '{app_module}': {e}")
                raise
            
    def run(self):
        """Inicia a API local e a janela desktop."""

        if self._config["api"]["enabled"]:
            self.api_server = ApiServer(
                api_router=api,
                host=self._config["api"]["host"],
                port=self._config["api"]["port"],
                debug=self._config["debug"],
            )

            self.logger.info(
                f"Iniciando API local em "
                f"http://{self._config['api']['host']}:{self._config['api']['port']}"
            )

            self.api_server.start()

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