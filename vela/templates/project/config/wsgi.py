"""
config/wsgi.py
Ponto de entrada da aplicação Vela.

Define apps instalados e inicializa o VelaApp.

Equivalente ao wsgi.py + urls.py do Django.
"""

from vela.core.app import VelaApp

# ─── Apps instalados ─────────────────────────────────────────────────────────
# Adicione seus apps aqui, na ordem em que deseja que apareçam na sidebar.

INSTALLED_APPS = [
    "apps.login",
    "apps.home",
    "apps.dashboard",
]


# ─── Função de boot ───────────────────────────────────────────────────────────

def run():
    # Opção A — via settings_module (legado, compatível)
    app = VelaApp(settings_module="config.settings")

    # Opção B — configuração direta (override)
    # app = VelaApp(
    #     title="Meu App",
    #     layout={
    #         "sidebar": True,
    #         "topbar":  True,
    #     }
    # )

    # Opção C — app sem sidebar (ex: ferramenta minimalista)
    # app = VelaApp(
    #     title="Mini Tool",
    #     layout={
    #         "sidebar": False,
    #         "topbar":  True,
    #     }
    # )

    for app_name in INSTALLED_APPS:
        app.register_app(app_name)

    app.run()
