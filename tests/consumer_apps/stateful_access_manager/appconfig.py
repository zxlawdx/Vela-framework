from vela.apps import AppConfig


class StatefulAccessManagerConfig(AppConfig):
    def __init__(self):
        base = "tests.consumer_apps.stateful_access_manager"
        super().__init__(
            name="stateful_access_manager",
            module=base,
            reloadable_modules=(base + ".views",),
            persistent_modules=(base + ".service",),
        )
