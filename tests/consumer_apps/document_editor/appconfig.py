from vela.apps import AppConfig


class DocumentEditorConfig(AppConfig):
    def __init__(self):
        super().__init__(name="document_editor", module="tests.consumer_apps.document_editor")
