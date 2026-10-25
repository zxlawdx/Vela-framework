"""Application entry point: collect local assets, register Home and start Vela."""

import sys

from config import settings
from config.bridge import StarterBridge
from vela.cli.collectstatic import collect_static
from vela.core.app import VelaApp

INSTALLED_APPS = ["apps.home"]


def run():
    # The packaged executable already includes collected assets.
    if not getattr(sys, "frozen", False):
        report = collect_static(
            output_dir=settings.STATIC_ROOT,
            skip_tailwind=True,
            asset_config={"tailwind": False},
            allow_install=False,
            verbose=False,
        )
        if report["errors"]:
            raise RuntimeError("Falha ao coletar os assets locais do starter.")
    app = VelaApp(settings_module="config.settings", bridge_class=StarterBridge)
    for app_name in INSTALLED_APPS:
        app.register_app(app_name)
    app.run()
