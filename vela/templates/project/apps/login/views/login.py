"""
apps.login.views.login
View da página de login.

Usa layout="blank" → sidebar e topbar são ocultadas pelo shell.
"""

from vela.template_engine.engine import render_template


def login_view(params: dict) -> str:
    """Retorna o HTML da tela de login (sem sidebar/topbar)."""
    return render_template("apps/login/templates/login.html", context={
        "titulo": "Home",
        "descricao": "Bem-vindo ao Vela.",
    },
        router=params["router"]
    )
