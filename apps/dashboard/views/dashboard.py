"""
apps.dashboard.views.dashboard
View principal do app dashboard.
"""
from vela.template_engine.engine import render_template

def dashboard_view(params: dict) -> str:
    """Retorna o HTML da página dashboard."""
    return render_template("apps/dashboard/templates/index.html",
    {
        "titulo": "dashboard",
        "descrição": "dashboard interativa"
    }
    )
