"""
vela.cli.shell
Shell interativo do Vela.
Abre um console Python com o contexto do framework já carregado.

Uso:
    python manage.py shell
"""

import code
import importlib
import sys
import os


BANNER = """
╔══════════════════════════════════════════════════════╗
║            Vela Framework — Shell Interativo         ║
╚══════════════════════════════════════════════════════╝

  Variáveis disponíveis:
    app        → instância do VelaApp
    router     → router do app
    bridge     → bridge Python↔JS
    settings   → configurações do projeto

  Exemplos:
    >>> router.list_routes()
    >>> bridge.ping()
    >>> app.bridge.get_framework_info()

  Sair: Ctrl+D  ou  exit()
"""


class VelaShell:
    def start(self):
        context = self._build_context()
        code.interact(banner=BANNER, local=context, exitmsg="\n  Shell Vela encerrado.\n")

    def _build_context(self) -> dict:
        context = {}

        try:
            from vela.core.app import VelaApp
            import config.wsgi as wsgi_module

            app = VelaApp()

            installed = getattr(wsgi_module, "INSTALLED_APPS", [])
            for app_name in installed:
                try:
                    app.register_app(app_name)
                except Exception as e:
                    print(f"  Aviso: não foi possível carregar '{app_name}': {e}")

            context["app"] = app
            context["router"] = app.router
            context["bridge"] = app.bridge
            context["settings"] = app._settings

        except Exception as e:
            print(f"\n  Aviso: não foi possível carregar o contexto completo: {e}")
            print("  Abrindo shell básico.\n")

        return context
