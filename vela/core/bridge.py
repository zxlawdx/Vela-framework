# SPDX-License-Identifier: MPL-2.0
"""Bridge mínima e validada entre JavaScript e Python."""
from __future__ import annotations

import json
from typing import Any

from vela.events import EventBus
from vela.log.logger import VelaLogger
from vela.runtime.hotreload import HotReloadManager


class BaseBridge:
    """Facade exposta ao ``window.pywebview.api``.

    Entradas da WebView são tratadas como não confiáveis. Métodos auxiliares
    internos começam com ``_``; pywebview não expõe nomes iniciados por underscore.
    """

    def __init__(
        self,
        router=None,
        config: dict | None = None,
        *,
        events: EventBus | None = None,
        hot_reload: HotReloadManager | None = None,
    ):
        self.router = router
        self.logger = VelaLogger("bridge")
        self.events = events or EventBus()
        self.hot_reload = hot_reload or HotReloadManager(enabled=False)
        self.config = config or {
            "title": "Vela App",
            "layout": {"sidebar": True, "topbar": True},
        }

    def get_config(self) -> dict:
        return self.config

    def navigate(self, path: str, params: str = "{}") -> dict[str, Any]:
        if not isinstance(path, str) or not path.startswith("/") or "\x00" in path:
            return {
                "ok": False,
                "html": "",
                "layout": "default",
                "theme": None,
                "path": str(path),
                "status": 400,
                "error_id": None,
            }
        if len(path) > 4096:
            return {
                "ok": False,
                "html": "",
                "layout": "default",
                "theme": None,
                "path": path[:4096],
                "status": 414,
                "error_id": None,
            }
        try:
            parsed_params = json.loads(params) if isinstance(params, str) else params
            if not isinstance(parsed_params, dict):
                parsed_params = {}
        except (json.JSONDecodeError, TypeError, ValueError):
            parsed_params = {}

        self.hot_reload.refresh()
        result = self.router.resolve(path, parsed_params)
        self.logger.info(
            f"navigate() → {path} [status={result.status}, layout={result.layout}]"
        )
        return {
            "ok": result.ok,
            "html": result.html,
            "layout": result.layout,
            "theme": result.theme,
            "path": path,
            "status": result.status,
            "error_id": result.error_id,
        }

    def get_routes(self) -> list:
        return self.router.get_sidebar_routes()

    def url_for(self, name: str) -> dict:
        if not isinstance(name, str) or len(name) > 512:
            return {"ok": False, "path": None, "error": "Nome de rota inválido."}
        try:
            return {"ok": True, "path": self.router.url_for(name)}
        except KeyError as exc:
            self.logger.warning(str(exc))
            return {"ok": False, "path": None, "error": str(exc)}

    def ping(self) -> str:
        return "pong"

    def get_framework_info(self) -> dict:
        import vela

        return {"name": "Vela Framework", "version": vela.__version__}

    def log(self, level: str, message: str):
        level = str(level).lower()
        message = str(message)[:4000]
        if level == "info":
            self.logger.info(f"[JS] {message}")
        elif level == "warning":
            self.logger.warning(f"[JS] {message}")
        elif level == "error":
            self.logger.error(f"[JS] {message}")
        else:
            self.logger.debug(f"[JS] {message}")

    def emit(self, name, payload=None):
        return self.events.emit(name, payload)

    def _attach_window(self, window):
        self.events.attach_window(window)
