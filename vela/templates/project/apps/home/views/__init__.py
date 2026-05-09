"""
apps.home — views
Registra as rotas do app home.
"""

from apps.home.views.home import home_view
from apps.dashboard.views import dashboard_view

def register_routes(router):
    router.add("/home", home_view, title="Home")
    router.add("/dashboard", dashboard_view, title="Dashboard")