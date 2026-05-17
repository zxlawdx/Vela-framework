"""
apps.home.views.__init__
Registra as rotas do app home.
"""

from apps.home.views.home import home_view


def register_routes(router):
    router.add(
        "/home",
        home_view,
        name="home",
        title="Home",
        icon="🏠",
        layout="default",
        show_in_sidebar=True,
        order=0,
    )
