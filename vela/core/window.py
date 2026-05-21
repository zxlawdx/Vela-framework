"""
vela.core.window
Gerenciador da janela desktop do Vela.
Usa pywebview para criar e exibir a janela nativa com HTML/CSS/JS.
"""

import webview

from vela.log.logger import VelaLogger


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
    ):
        self.title = title
        self.width = width
        self.height = height
        self.bridge = bridge
        self.debug = debug
        self.entry_route = entry_route
        self.host = host
        self.port = port
        self.logger = VelaLogger("Window")

    def _get_shell_url(self) -> str:
        return (
            f"http://{self.host}:{self.port}"
            f"/__vela__/shell?entry={self.entry_route}"
        )

    def run(self):
        """Cria e exibe a janela desktop."""
        shell_url = self._get_shell_url()

        self.logger.info(
            f"Carregando shell: {shell_url}"
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
            window.evaluate_js(f"""
                window.__VELA_ENTRY__ = "{self.entry_route}";
            """)

        window.events.loaded += on_loaded

        webview.start(debug=self.debug)

        self.logger.info(
            "Janela encerrada."
        )