from .dashboard import dashboard
from ..service import SESSION, PROVIDER


def register_routes(router):
    router.add("/access", dashboard, name="access", title="Access")
