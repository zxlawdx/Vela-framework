from vela.apps import AppConfig


class MinimalDFDConfig(AppConfig):
    def __init__(self):
        super().__init__(
            name="minimal_dfd",
            module="tests.consumer_apps.minimal_dfd",
            static_dirs=("tests/consumer_apps/minimal_dfd/static",),
        )
