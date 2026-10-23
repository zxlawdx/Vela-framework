from ..service import PROVIDER as PROVIDER
from ..service import SESSION as SESSION
from .dashboard import dashboard


def register_routes(router):
    router.add("/access", dashboard, name="access", title="Access")
