"""
dashboard — views
Registra as rotas deste app no router do Vela.
"""

from apps.dashboard.views.dashboard import dashboard_view


def register_routes(router):
    router.add("/dashboard", dashboard_view, title="Dashboard")
