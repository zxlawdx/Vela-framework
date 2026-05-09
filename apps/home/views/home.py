"""
apps.home.views.home
View da página principal.

No Vela, uma view é uma função Python que recebe params
e retorna uma string HTML. Simples assim.
"""


from vela.template_engine.engine import render_template


def home_view(params: dict) -> str:
    """Retorna o HTML da página Home."""

    return render_template("apps/home/templates/home.html", {
        "titulo": "Home",
        "descricao": "Bem-vindo ao Vela.",
    })
