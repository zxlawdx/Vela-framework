"""
apps.dashboard.views.__init__
Registra as rotas do app dashboard.
"""

from apps.dashboard.views.dashboard import dashboard_view


def register_routes(router):
    router.add(
        "/dashboard",
        dashboard_view,
        name="dashboard",
        title="Dashboard",
        icon="📊",
        layout="default",
        show_in_sidebar=True,
        order=1,
    )
