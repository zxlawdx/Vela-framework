# SPDX-License-Identifier: MPL-2.0
"""Composition root público do Vela Framework."""

from __future__ import annotations

import importlib

from vela.api import api
from vela.apps import AppConfig, AppRegistry
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
    def __init__(self, title=None, layout=None, settings_module="config.settings", bridge_class=None, enable_api=True, window_backend_class=None, http_server_class=None):
        self.logger = VelaLogger("app")
        self._config_loader = ConfigLoader(settings_module)
        self._settings = self._config_loader.load_module()
        self.config = self._config_loader.load(title=title, layout=layout, enable_api=enable_api)
        self._config = self.config.to_dict()
        self.enable_api = enable_api
        self.apps = AppRegistry()
        self.router = Router(); self.router.debug = self.config.debug
        self.api_router = api.new_router()
        self.events = EventBus()
        self.lifecycle = LifecycleManager(); self.lifecycle.configured()
        self.hot_reload = HotReloadManager(enabled=self.config.debug)
        self.hot_reload.add_reload_callback(self.router.refresh_module)
        self.hot_reload.add_reload_callback(self.api_router.refresh_module)
        self.hot_reload.set_reload_context(lambda: api.bind(self.api_router))
        bridge_cls = bridge_class or BaseBridge
        self.bridge = bridge_cls(router=self.router, config=self._config)
        if hasattr(self.bridge, "events"): self.bridge.events = self.events
        if hasattr(self.bridge, "hot_reload"): self.bridge.hot_reload = self.hot_reload
        self._window_backend_class = window_backend_class or DesktopWindow
        self._http_server_class = http_server_class or ApiServer
        self.api_server = None; self._window = None; self._closed = False
        self.lifecycle.on_shutdown(self.hot_reload.stop)
        self.lifecycle.on_shutdown(self.events.clear)
        if self.config.shell_mode == "http": self.router.base_url = f"http://{self.config.api.host}:{self.config.api.port}"

    @staticmethod
    def _import_optional(target: str):
        try: return importlib.import_module(target)
        except ModuleNotFoundError as exc:
            if is_missing_target(exc, target): return None
            raise

    def _track_app_module(self, module, config: AppConfig) -> None:
        if module is None: return
        name = module.__name__
        persistent = any(name == prefix or name.startswith(prefix + ".") for prefix in config.persistent_modules)
        reloadable = any(name == prefix or name.startswith(prefix + ".") for prefix in config.reloadable_modules)
        self.hot_reload.track_module(module, reloadable=reloadable and not persistent)

    def register_app(self, app: str | AppConfig | type[AppConfig]):
        config = self.apps.register(app); loaded = []
        with api.bind(self.api_router):
            views_module = self._import_optional(config.views_module)
            if views_module is not None:
                loaded.append(views_module)
                register_routes = getattr(views_module, "register_routes", None)
                if callable(register_routes): register_routes(self.router)
            urls_module = self._import_optional(config.urls_module)
            if urls_module is not None: loaded.append(urls_module)
            api_module = self._import_optional(config.api_module)
            if api_module is not None: loaded.append(api_module)
        for module in loaded: self._track_app_module(module, config)
        for prefix in config.persistent_modules: self.hot_reload.protect_prefix(prefix)
        return self

    def run(self):
        c = self._config; self.lifecycle.startup()
        try:
            if c["api"]["enabled"]:
                self.api_server = self._http_server_class(
                    api_router=self.api_router, host=c["api"]["host"], port=c["api"]["port"],
                    prefix=c["api"].get("prefix", "/api"), debug=c["debug"], static_root=c.get("static_root", "staticfiles"),
                    auto_port=c["api"].get("auto_port", True), server=c["api"].get("server", "waitress"),
                    docs_enabled=c["api"].get("docs_enabled", True), workers=c["api"].get("workers", 4),
                    allow_remote=c["api"].get("allow_remote", False), cors_origins=c["api"].get("cors_origins", ()),
                    max_body_size=c["api"].get("max_body_size", 1_048_576),
                )
                requested_port = c["api"]["port"]; actual_port = self.api_server.start()
                self.lifecycle.on_shutdown(self.api_server.stop); c["api"]["port"] = actual_port
                if c.get("shell_mode", "http") == "http": self.router.base_url = f"http://{c['api']['host']}:{actual_port}"
                if actual_port != requested_port: self.logger.warning(f"Porta {requested_port} indisponível; API iniciou em {actual_port}.")
                self.api_server.wait_until_ready()
            self._window = self._window_backend_class(
                title=c["title"], width=c["window"]["width"], height=c["window"]["height"], bridge=self.bridge,
                debug=c["debug"], entry_route=c["entry_route"], host=c["api"]["host"], port=c["api"]["port"],
                shell_mode=c.get("shell_mode", "http"), icon=c.get("icon", ""),
            )
            stop_window = getattr(self._window, "stop", None)
            if callable(stop_window): self.lifecycle.on_shutdown(stop_window)
            self.lifecycle.running(); self._window.run()
        finally: self.stop()

    def stop(self):
        if self._closed: return
        self._closed = True; self.lifecycle.shutdown()

    def close(self): self.stop()
