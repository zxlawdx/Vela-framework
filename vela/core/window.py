# SPDX-License-Identifier: MPL-2.0
"""
vela.core.window
================
Gerenciador da janela desktop do Vela.
Usa pywebview para criar e exibir a janela nativa com HTML/CSS/JS.

Modos de carregamento do shell:
  shell_mode = "http"   → http://127.0.0.1:PORT/__vela__/shell  (recomendado)
  shell_mode = "file"   → file:///path/to/shell.html             (legado)

O modo "http" elimina problemas de CORS quando páginas fazem fetch para /api/...
pois a origin fica consistente em http://127.0.0.1:PORT.
"""

from pathlib import Path
import os
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
        self.logger = VelaLogger("Window")

    def _get_shell_url(self) -> str:
        if self.shell_mode == "file":
            # Modo legado: carrega o arquivo diretamente.
            # Atenção: fetch() para http://127.0.0.1/api/... causará CORS neste modo.
            shell_path = CORE_DIR / "shell.html"
            # Em modo file://, a entry_route é passada via __VELA_ENTRY__ no on_loaded,
            # pois não há query string disponível de forma confiável.
            return shell_path.as_uri()
        else:
            # Modo http: shell servido pelo Bottle interno.
            # entry_route é passada como query string — lida pelo JS antes da bridge.
            return (
                f"http://{self.host}:{self.port}"
                f"/__vela__/shell?entry={self.entry_route}"
            )

    def run(self):
        """Cria e exibe a janela desktop."""
        shell_url = self._get_shell_url()

        self.logger.info(
            f"Carregando shell [{self.shell_mode}]: {shell_url}"
        )

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
            # Injeta __VELA_ENTRY__ em ambos os modos.
            # Em modo http, funciona como fallback caso a query string não seja lida.
            # Em modo file, é o mecanismo principal.
            window.evaluate_js(
                f'window.__VELA_ENTRY__ = "{self.entry_route}";'
            )

        window.events.loaded += on_loaded
        if self.bridge and hasattr(self.bridge, "_attach_window"):
            self.bridge._attach_window(window)


        # Qt e GTK aceitam icone no start; Windows usa icone do executavel.
        icon_file = Path(self.icon) if self.icon else None
        if not icon_file or not icon_file.is_file():
            import json
            manifest = Path.cwd() / ".vela-app.json"
            if manifest.is_file():
                try:
                    meta = json.loads(manifest.read_text(encoding="utf-8"))
                    icon_file = Path.cwd() / meta.get("icon", "")
                except (ValueError, OSError):
                    icon_file = None
        icon_arg = str(icon_file.resolve()) if icon_file and icon_file.is_file() else None
        gui = os.environ.get("VELA_GUI") or None
        webview.start(gui=gui, debug=self.debug, icon=icon_arg)

        self.logger.info("Janela encerrada.")