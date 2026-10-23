# SPDX-License-Identifier: MPL-2.0
"""Composition root público do Vela Framework."""
from __future__ import annotations

import importlib

from vela.api import api
from vela.config import ConfigLoader, is_missing_target
from vela.core.api_server import ApiServer
from vela.core.bridge import BaseBridge
from vela.core.router import Router
from vela.core.window import DesktopWindow
from vela.events import EventBus
from vela.log.logger import VelaLogger
from vela.runtime.hotreload import HotReloadManager
from vela.runtime.lifecycle import LifecycleManager


class VelaApp:
    """Facade pública; composição e lifecycle ficam explícitos internamente."""

    def __init__(
        self,
        title: str | None = None,
        layout: dict | None = None,
        settings_module: str = "config.settings",
        bridge_class=None,
        enable_api: bool = True,
        window_backend_class=None,
        http_server_class=None,
    ):
        self.logger = VelaLogger("app")
        self._config_loader = ConfigLoader(settings_module)
        self._settings = self._config_loader.load_module()
        self.config = self._config_loader.load(
            title=title, layout=layout, enable_api=enable_api
        )
        self._config = self.config.to_dict()
        self.enable_api = enable_api

        self.router = Router()
        self.router.debug = self.config.debug
        self.api_router = api.new_router()
        self.events = EventBus()
        self.lifecycle = LifecycleManager()
        self.hot_reload = HotReloadManager(enabled=self.config.debug)
        self.hot_reload.add_reload_callback(self.router.refresh_module)
        self.hot_reload.add_reload_callback(self.api_router.refresh_module)
        self.hot_reload.set_reload_context(lambda: api.bind(self.api_router))

        bridge_cls = bridge_class or BaseBridge
        self.bridge = bridge_cls(router=self.router, config=self._config)
        if hasattr(self.bridge, "events"):
            self.bridge.events = self.events
        if hasattr(self.bridge, "hot_reload"):
            self.bridge.hot_reload = self.hot_reload

        self._window_backend_class = window_backend_class or DesktopWindow
        self._http_server_class = http_server_class or ApiServer
        self.api_server = None
        self._closed = False
        self.lifecycle.on_shutdown(self.events.clear)

        if self.config.shell_mode == "http":
            self.router.base_url = (
                f"http://{self.config.api.host}:{self.config.api.port}"
            )

        self.logger.info(
            f"Vela configurado | title={self.config.title} "
            f"| sidebar={self.config.layout.sidebar} "
            f"| topbar={self.config.layout.topbar} "
            f"| api={self.config.api.enabled}"
        )

    def _load_settings(self, module_path: str):
        return ConfigLoader(module_path).load_module()

    def _build_config(
        self, title: str | None = None, layout: dict | None = None
    ) -> dict:
        return self._config_loader.load(
            title=title,
            layout=layout,
            enable_api=self.enable_api,
        ).to_dict()

    @staticmethod
    def _import_optional(target: str):
        try:
            return importlib.import_module(target)
        except ModuleNotFoundError as exc:
            if is_missing_target(exc, target):
                return None
            raise

    def register_app(self, app_module: str):
        if not isinstance(app_module, str) or not app_module:
            raise ValueError("app_module deve ser uma string não vazia.")
        with api.bind(self.api_router):
            views_module = self._import_optional(f"{app_module}.views")
            if views_module is not None:
                register_routes = getattr(views_module, "register_routes", None)
                if callable(register_routes):
                    register_routes(self.router)
                    self.logger.info(f"Views do app {app_module!r} registradas.")
                else:
                    self.logger.warning(
                        f"App {app_module!r} possui views, mas não register_routes()."
                    )

            urls_module = self._import_optional(f"{app_module}.urls")
            if urls_module is not None:
                self.logger.info(f"URLs do app {app_module!r} carregadas.")

            api_module = self._import_optional(f"{app_module}.api")
            if api_module is not None:
                self.logger.info(f"API do app {app_module!r} carregada.")

        self.hot_reload.track_loaded_prefix(app_module)
        return self

    def run(self):
        c = self._config
        self.lifecycle.startup()
        try:
            if c["api"]["enabled"]:
                self.lifecycle.transition("api_start")
                self.api_server = self._http_server_class(
                    api_router=self.api_router,
                    host=c["api"]["host"],
                    port=c["api"]["port"],
                    debug=c["debug"],
                    static_root=c.get("static_root", "staticfiles"),
                    auto_port=c["api"].get("auto_port", True),
                    server=c["api"].get("server", "waitress"),
                    docs_enabled=c["api"].get("docs_enabled", True),
                    workers=c["api"].get("workers", 4),
                    allow_remote=c["api"].get("allow_remote", False),
                    cors_origins=c["api"].get("cors_origins", ()),
                    max_body_size=c["api"].get("max_body_size", 1_048_576),
                )
                requested_port = c["api"]["port"]
                actual_port = self.api_server.start()
                self.lifecycle.on_shutdown(self.api_server.stop)
                c["api"]["port"] = actual_port
                if c.get("shell_mode", "http") == "http":
                    self.router.base_url = f"http://{c['api']['host']}:{actual_port}"
                if actual_port != requested_port:
                    self.logger.warning(
                        f"Porta {requested_port} indisponível; API iniciou em {actual_port}."
                    )
                self.api_server.wait_until_ready()

            self.lifecycle.transition("window_start")
            window = self._window_backend_class(
                title=c["title"],
                width=c["window"]["width"],
                height=c["window"]["height"],
                bridge=self.bridge,
                debug=c["debug"],
                entry_route=c["entry_route"],
                host=c["api"]["host"],
                port=c["api"]["port"],
                shell_mode=c.get("shell_mode", "http"),
                icon=c.get("icon", ""),
            )
            self.lifecycle.transition("running")
            window.run()
        finally:
            self.close()

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.lifecycle.shutdown()
