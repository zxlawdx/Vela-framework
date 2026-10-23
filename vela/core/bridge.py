# SPDX-License-Identifier: MPL-2.0
"""Validated JavaScript/Python bridge facade."""

from __future__ import annotations

import json
from typing import Any

from vela.events import EventBus
from vela.log.logger import VelaLogger
from vela.platform import PlatformServices
from vela.runtime.hotreload import HotReloadManager


class BaseBridge:
    """Explicit facade exposed to ``window.pywebview.api``.

    JavaScript input is untrusted. Public methods validate sizes/types and the
    implementation keeps internal helpers private.
    """

    def __init__(self, router=None, config=None, *, events=None, hot_reload=None, platform=None):
        self.router = router
        self.logger = VelaLogger("bridge")
        self.events = events or EventBus()
        self.hot_reload = hot_reload or HotReloadManager(enabled=False)
        self.platform = platform or PlatformServices.detect()
        self.config = config or {"title": "Vela App", "layout": {"sidebar": True, "topbar": True}}
        self._window = None

    def get_config(self) -> dict:
        import vela

        value = dict(self.config)
        value["vela_version"] = vela.__version__
        return value

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
        if isinstance(params, str) and len(params) > 2 * 1024 * 1024:
            return {
                "ok": False,
                "html": "",
                "layout": "default",
                "theme": None,
                "path": path,
                "status": 413,
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
            return {"ok": False, "path": None, "error": str(exc)}

    def capabilities(self) -> dict[str, object]:
        """Native capabilities only; browser/GPU features are probed in JS."""
        return self.platform.capabilities()

    def clipboard_write_text(self, text: str) -> dict[str, object]:
        if not isinstance(text, str):
            return {"ok": False, "error": "clipboard text must be a string"}
        if len(text.encode("utf-8")) > 2 * 1024 * 1024:
            return {"ok": False, "error": "clipboard payload too large"}
        try:
            ok = self.platform.clipboard.write_text(text)
        except Exception as exc:
            self.logger.exception(f"Falha no clipboard nativo: {exc}")
            ok = False
        return {"ok": bool(ok)}

    def ping(self) -> str:
        return "pong"

    def get_framework_info(self) -> dict:
        import vela

        return {"name": "Vela Framework", "version": vela.__version__}

    def log(self, level: str, message: str):
        level = str(level).lower()
        message = str(message)[:4000]
        target = getattr(
            self.logger, level if level in {"info", "warning", "error", "debug"} else "debug"
        )
        target(f"[JS] {message}")

    def emit(self, name, payload=None):
        if not isinstance(name, str) or not name or len(name) > 256:
            return False
        return self.events.emit(name, payload)

    def _attach_window(self, window):
        self._window = window
        self.events.attach_window(window)
