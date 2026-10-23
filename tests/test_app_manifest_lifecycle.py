# SPDX-License-Identifier: MPL-2.0
import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

from vela.apps import AppConfig, AppRegistry
from vela.runtime.hotreload import HotReloadManager
from vela.runtime.lifecycle import LifecycleManager, LifecycleState


class AppManifestTests(unittest.TestCase):
    def test_legacy_app_is_normalized_to_explicit_manifest(self):
        registry = AppRegistry()
        config = registry.register("apps.dfd")
        self.assertEqual(config.name, "dfd")
        self.assertEqual(config.views_module, "apps.dfd.views")
        self.assertEqual(config.api_module, "apps.dfd.api")
        self.assertIn("apps.dfd.views", config.reloadable_modules)
        self.assertNotIn("apps.dfd.api", config.reloadable_modules)

    def test_manifest_exposes_build_discovery_inputs(self):
        config = AppConfig(
            name="editor",
            module="apps.editor",
            hidden_imports=("pypdf",),
            resources=("resources/fonts",),
        )
        metadata = config.build_metadata()
        self.assertIn("apps.editor.api", metadata["modules"])
        self.assertIn("pypdf", metadata["modules"])
        self.assertEqual(metadata["resources"], ["resources/fonts"])


class LifecycleContractTests(unittest.TestCase):
    def test_state_machine_and_shutdown_are_deterministic(self):
        calls = []
        lifecycle = LifecycleManager()
        self.assertEqual(lifecycle.state, LifecycleState.CREATED)
        lifecycle.configured()
        lifecycle.on_startup(lambda: calls.append("start"))
        lifecycle.on_shutdown(lambda: calls.append("stop-a"))
        lifecycle.on_shutdown(lambda: calls.append("stop-b"))
        lifecycle.startup()
        lifecycle.running()
        self.assertEqual(lifecycle.state, LifecycleState.RUNNING)
        lifecycle.shutdown()
        lifecycle.shutdown()
        self.assertEqual(lifecycle.state, LifecycleState.STOPPED)
        self.assertEqual(calls, ["start", "stop-b", "stop-a"])

    def test_invalid_transition_fails_early(self):
        lifecycle = LifecycleManager()
        with self.assertRaises(RuntimeError):
            lifecycle.running()


class StatefulHotReloadTests(unittest.TestCase):
    def test_dirty_view_reloads_but_persistent_service_keeps_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "consumer_stateful"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            view_path = package / "view.py"
            service_path = package / "service.py"
            view_path.write_text("VALUE = 'v1'\n", encoding="utf-8")
            service_path.write_text("SESSION = object()\n", encoding="utf-8")
            sys.path.insert(0, directory)
            try:
                view = importlib.import_module("consumer_stateful.view")
                service = importlib.import_module("consumer_stateful.service")
                session = service.SESSION
                manager = HotReloadManager(enabled=True)
                manager.track_module(view, reloadable=True)
                manager.protect_prefix("consumer_stateful.service")
                manager.track_module(service, reloadable=False)

                original = view_path.stat().st_mtime_ns
                view_path.write_text("VALUE = 'version-two'\n", encoding="utf-8")
                os.utime(view_path, ns=(original + 2_000_000_000, original + 2_000_000_000))
                reloaded = manager.refresh()

                self.assertEqual(reloaded, ("consumer_stateful.view",))
                self.assertEqual(sys.modules["consumer_stateful.view"].VALUE, "version-two")
                self.assertIs(sys.modules["consumer_stateful.service"].SESSION, session)
            finally:
                sys.path.remove(directory)
                for name in tuple(sys.modules):
                    if name == "consumer_stateful" or name.startswith("consumer_stateful."):
                        sys.modules.pop(name, None)


if __name__ == "__main__":
    unittest.main()
