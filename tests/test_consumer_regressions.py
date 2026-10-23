# SPDX-License-Identifier: MPL-2.0
import sys
import unittest
from pathlib import Path

from vela.core.app import VelaApp
from vela.runtime.lifecycle import LifecycleState
from tests.consumer_apps.minimal_dfd.appconfig import MinimalDFDConfig
from tests.consumer_apps.stateful_access_manager.appconfig import StatefulAccessManagerConfig
from tests.consumer_apps.document_editor.appconfig import DocumentEditorConfig


class ConsumerRegressionTests(unittest.TestCase):
    def make_app(self):
        return VelaApp(enable_api=False, settings_module="tests.missing_consumer_settings")

    def test_dfd_manifest_auto_registers_page_and_api_without_manual_import(self):
        sys.modules.pop("tests.consumer_apps.minimal_dfd.api", None)
        app = self.make_app()
        app.register_app(MinimalDFDConfig)
        self.assertTrue(app.router.resolve("/dfd").ok)
        route = app.api_router.get_route("GET", "/dfd/status")
        self.assertIsNotNone(route)
        self.assertEqual(len(app.apps), 1)
        app.stop()

    def test_access_manager_stateful_modules_are_persistent(self):
        app = self.make_app()
        app.register_app(StatefulAccessManagerConfig)
        from tests.consumer_apps.stateful_access_manager import service

        session = service.SESSION
        provider = service.PROVIDER
        items = {item.name: item for item in app.hot_reload.registry.values()}
        self.assertIn("tests.consumer_apps.stateful_access_manager.service", items)
        self.assertFalse(items["tests.consumer_apps.stateful_access_manager.service"].reloadable)
        self.assertIn("tests.consumer_apps.stateful_access_manager.views.dashboard", items)
        self.assertTrue(
            items["tests.consumer_apps.stateful_access_manager.views.dashboard"].reloadable
        )
        self.assertIs(service.SESSION, session)
        self.assertIs(service.PROVIDER, provider)
        self.assertEqual(service.Provider.instances, 1)
        page = app.router.resolve("/access")
        self.assertIn("<canvas", page.html)
        app.stop()

    def test_open_doc_fixture_keeps_editor_selection_canvas_and_api(self):
        app = self.make_app()
        app.register_app(DocumentEditorConfig)
        page = app.router.resolve("/editor")
        self.assertTrue(page.ok)
        self.assertIn('contenteditable="true"', page.html)
        self.assertIn('class="textLayer"', page.html)
        self.assertIn("<canvas", page.html)
        self.assertIsNotNone(app.api_router.get_route("POST", "/documents/save"))
        shell = (Path(__file__).parents[1] / "vela/core/shell.html").read_text(encoding="utf-8")
        self.assertNotIn("user-select: none", shell)
        self.assertNotIn("navigator.clipboard", shell)
        app.stop()

    def test_stop_without_run_is_idempotent(self):
        app = self.make_app()
        app.stop()
        app.stop()
        self.assertEqual(app.lifecycle.state, LifecycleState.STOPPED)


if __name__ == "__main__":
    unittest.main()
