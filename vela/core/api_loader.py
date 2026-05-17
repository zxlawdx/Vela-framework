import importlib
import os


def load_app_apis(apps_dir="apps"):
    if not os.path.exists(apps_dir):
        return

    for app_name in os.listdir(apps_dir):
        api_file = os.path.join(apps_dir, app_name, "api.py")

        if os.path.exists(api_file):
            importlib.import_module(f"apps.{app_name}.api")