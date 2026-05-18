"""
apps.login.views.__init__
Registra as rotas do app login.

O layout "blank" esconde sidebar e topbar — perfeito para telas de login.
"""

from apps.login.views.login import login_view


def register_routes(router):
    router.add(
        "/",
        login_view,
        name="login",
        title="Login",
        layout="blank",        # <── esconde sidebar e topbar
        show_in_sidebar=False, # <── não aparece na sidebar
        order=999,
    )
