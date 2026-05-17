"""
vela.core.window
Gerenciador da janela desktop do Vela.
Usa pywebview para criar e exibir a janela nativa com HTML/CSS/JS.
"""

import os
import webview
from vela.log.logger import VelaLogger
from pathlib import Path
from vela.templates.project.config.settings import ENTRY_ROUTE 

SHELL_HTML = os.path.join(os.path.dirname(__file__), "shell.html")


class DesktopWindow:
    def __init__(
        self,
        title: str = "Vela App",
        width: int = 1200,
        height: int = 800,
        bridge=None,
        debug: bool = False,
        entry_route: str = "/",
    ):
        self.title = title
        self.width = width
        self.height = height
        self.bridge = bridge
        self.debug = debug
        self.entry_route = entry_route
        self.logger = VelaLogger("Window")

    def _get_shell_html(self) -> str:
        """
        Retorna o HTML base que o pywebview vai carregar.
        Este HTML é o 'shell' da aplicação — ele carrega o CSS e o JS do app,
        mas o conteúdo de cada página vem via Python através da bridge.
        """
        # Procura o shell.html relativo ao projeto root
        project_root = os.getcwd()
        BASE_DIR = Path(__file__).resolve().parent
        shell_path = BASE_DIR / "shell.html"
        return shell_path

    def run(self):
        """Cria e exibe a janela desktop."""
        shell_path = self._get_shell_html()

        if not os.path.exists(shell_path):
            self.logger.error(f"shell.html não encontrado em: {shell_path}")
            raise FileNotFoundError(f"shell.html não encontrado em: {shell_path}")

        shell_url = shell_path.resolve().as_uri()

        self.logger.info(f"Carregando shell: {shell_url}")

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

                if (window.navigate) {{
                    window.navigate("{self.entry_route}");
                }}
            """)

        window.events.loaded += on_loaded

        webview.start(debug=self.debug)
        self.logger.info("Janela encerrada.")