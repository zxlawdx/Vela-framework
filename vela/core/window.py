# SPDX-License-Identifier: MPL-2.0
"""Adapter pywebview da janela desktop."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlencode

import webview

from vela.log.logger import VelaLogger

CORE_DIR = Path(__file__).resolve().parent


class DesktopWindow:
    def __init__(
        self,
        title: str = "Vela App",
        width: int = 1200,
        height: int = 800,
        bridge=None,
        debug: bool = False,
        entry_route: str = "/",
        host: str = "127.0.0.1",
        port: int = 8000,
        shell_mode: str = "http",
        icon: str = "",
    ):
        self.title = title
        self.width = width
        self.height = height
        self.bridge = bridge
        self.debug = debug
        self.entry_route = entry_route
        self.host = host
        self.port = port
        self.shell_mode = shell_mode
        self.icon = icon
        self.logger = VelaLogger("window")

    def _get_shell_url(self) -> str:
        if self.shell_mode == "file":
            return (CORE_DIR / "shell.html").as_uri()
        target_host = (
            "127.0.0.1"
            if self.host == "0.0.0.0"
            else "::1"
            if self.host == "::"
            else self.host
        )
        host_for_url = (
            f"[{target_host}]"
            if ":" in target_host and not target_host.startswith("[")
            else target_host
        )
        query = urlencode({"entry": self.entry_route})
        return f"http://{host_for_url}:{self.port}/__vela__/shell?{query}"

    def run(self):
        shell_url = self._get_shell_url()
        self.logger.info(f"Carregando shell [{self.shell_mode}]: {shell_url}")
        window = webview.create_window(
            title=self.title,
            url=shell_url,
            width=self.width,
            height=self.height,
            js_api=self.bridge,
            resizable=True,
            frameless=False,
            easy_drag=False,
        )

        def on_loaded():
            window.evaluate_js(f"window.__VELA_ENTRY__ = {json.dumps(self.entry_route)};")

        window.events.loaded += on_loaded
        if self.bridge and hasattr(self.bridge, "_attach_window"):
            self.bridge._attach_window(window)

        icon_file = Path(self.icon) if self.icon else None
        if not icon_file or not icon_file.is_file():
            manifest = Path.cwd() / ".vela-app.json"
            if manifest.is_file():
                try:
                    meta = json.loads(manifest.read_text(encoding="utf-8"))
                    candidate = Path.cwd() / str(meta.get("icon", ""))
                    icon_file = candidate if candidate.is_file() else None
                except (ValueError, OSError, TypeError):
                    icon_file = None
        icon_arg = str(icon_file.resolve()) if icon_file and icon_file.is_file() else None
        gui = os.environ.get("VELA_GUI") or None
        webview.start(gui=gui, debug=self.debug, icon=icon_arg)
        self.logger.info("Janela encerrada.")
