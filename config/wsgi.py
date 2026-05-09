"""
config/wsgi.py
Ponto de entrada da aplicação Vela.
Define quais apps estão instalados e inicia o VelaApp.

Equivalente ao wsgi.py + urls.py do Django.
"""

from vela.core.app import VelaApp

# ─── Apps instalados ─────────────────────────────────────────────────────────
# Adicione seus apps aqui, na ordem em que deseja que apareçam na sidebar.

INSTALLED_APPS = [
    "apps.home",
    "apps.dashboard",
]


# ─── Função de boot ───────────────────────────────────────────────────────────

def run():
    app = VelaApp(settings_module="config.settings")

    for app_name in INSTALLED_APPS:
        app.register_app(app_name)

    app.run()
