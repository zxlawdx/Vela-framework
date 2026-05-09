"""
apps.dashboard.views.dashboard
View principal do dashboard.
"""

from vela.template_engine.engine import render_template


def dashboard_view(params: dict) -> str:
    """Retorna o HTML da página Dashboard."""
    return render_template(
        "apps/dashboard/templates/index.html",
        {
            "titulo": "Dashboard",
            "descricao": "Visão geral do sistema.",
        },
    )
