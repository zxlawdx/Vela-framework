# SPDX-License-Identifier: MPL-2.0
"""Testes de build, instalacao e diagnostico sem compilar nem usar rede."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vela.cli.build import (BuildOptions, backend_for, build_app,
                            build_plan, identity, launcher_source)
from vela.cli.doctor import Check, missing_pip_packages, remedy
from vela.cli.install import desktop_entry, install_bundle, uninstall_app
from vela.cli.workflow import generate_workflow


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "config").mkdir()
        (self.root / "apps").mkdir()
        (self.root / "manage.py").write_text("# test\n")
        (self.root / "config/settings.py").write_text(
            "APP_TITLE='Teste Vela'\nAPP_VERSION='0.2.0'\n"
            "APP_FILE_EXTENSIONS=['.dfd.json']\n")

    def test_native_backends(self):
        self.assertEqual(backend_for("auto", "linux"), "qt6")
        self.assertEqual(backend_for("auto", "windows"), "native")
        with self.assertRaises(ValueError):
            backend_for("gtk", "windows")

    def test_dry_run_never_writes_files(self):
        results = build_app(self.root, BuildOptions(dry_run=True, gui="qt6"),
                            notify=lambda _: None)
        self.assertEqual(results["meta"]["slug"], "Teste-Vela")
        self.assertIn("apps", results["command"])
        self.assertIn("qtpy", results["command"])
        self.assertFalse((self.root / ".vela-build").exists())
        self.assertFalse((self.root / "staticfiles").exists())

    def test_launcher_contains_qt_and_system_install_switch(self):
        s = launcher_source("qt6")
        compile(s, "__vela_launcher__.py", "exec")
        self.assertIn("QT_XCB_GL_INTEGRATION", s)
        self.assertIn("--vela-install", s)
        self.assertIn('VELA_PRODUCTION', s)
        self.assertIn('scope = "system" if "--scope=system" in sys.argv', s)
        self.assertIn('"--vela-install" not in sys.argv', s)
        self.assertIn('PYWEBVIEW_GUI', launcher_source("gtk"))
        self.assertIn('import qtpy', s)
        self.assertIn('import webview.platforms.qt', s)
        self.assertIn('import webview.platforms.gtk', launcher_source("gtk"))
        self.assertIn('VELA_GUI', s)
        self.assertNotIn("sudo", s)

    def test_builder_checks_frozen_gui_runtime(self):
        import inspect
        from vela.core.window import DesktopWindow
        self.assertIn("webview.start(gui=gui", inspect.getsource(DesktopWindow.run))
        self.assertIn('"--self-test"', inspect.getsource(build_app))
        gtk = build_plan(self.root, BuildOptions(gui="gtk"))
        self.assertIn("gi", gtk["command"])
        self.assertIn("webview.platforms.gtk", gtk["command"])

    def test_pkg_resources_collects_jaraco_only_when_needed(self):
        from vela.cli.build import (LEGACY_PKG_RESOURCES_MODULES,
                                    legacy_pkg_resources_collect_args,
                                    validate_legacy_pkg_resources)
        with patch("vela.cli.build._module_exists",
                   side_effect=lambda name: name == "pkg_resources"
                   or name in LEGACY_PKG_RESOURCES_MODULES):
            flags = legacy_pkg_resources_collect_args()
            self.assertIn("setuptools", flags)
            self.assertIn("pkg_resources", flags)
            for module in LEGACY_PKG_RESOURCES_MODULES:
                self.assertIn(module, flags)
            validate_legacy_pkg_resources()
        with patch("vela.cli.build._module_exists", return_value=False):
            self.assertEqual(legacy_pkg_resources_collect_args(), [])
            validate_legacy_pkg_resources()

    def test_venv_detection_uses_pyvenv_cfg(self):
        from vela.cli.build import linux_venv_info
        fake_venv = self.root / "venv"
        fake_venv.mkdir()
        cfg = fake_venv / "pyvenv.cfg"
        with patch("vela.cli.build.sys.prefix", str(fake_venv)):
            with patch("vela.cli.build.sys.base_prefix", "/usr"):
                cfg.write_text("home = /usr/bin\ninclude-system-site-packages = true\n")
                info = linux_venv_info()
                self.assertTrue(info["active"])
                self.assertTrue(info["system_site_packages"])
                cfg.write_text("include-system-site-packages = false\n")
                self.assertFalse(linux_venv_info()["system_site_packages"])

    def test_qt_shared_venv_and_gtk_isolated_are_reported(self):
        from vela.cli.build import gui_venv_messages
        with patch("vela.cli.build.platform.system", return_value="Linux"):
            with patch("vela.cli.build.linux_venv_info",
                       return_value={"active": True,
                                     "system_site_packages": True}):
                self.assertIn("--system-site-packages",
                              gui_venv_messages("qt6")[0])
            with patch("vela.cli.build.linux_venv_info",
                       return_value={"active": True,
                                     "system_site_packages": False}):
                with patch("vela.cli.build._module_exists", return_value=False):
                    self.assertIn("--system-site-packages",
                                  gui_venv_messages("gtk")[0])
                with patch("vela.cli.build._module_exists", return_value=True):
                    self.assertEqual(gui_venv_messages("gtk"), [])
            with patch("vela.cli.build.linux_venv_info",
                       return_value={"active": False,
                                     "system_site_packages": False}):
                self.assertEqual(gui_venv_messages("gtk"), [])

    def test_missing_jaraco_fails_before_build(self):
        from vela.cli.build import validate_legacy_pkg_resources
        with patch("vela.cli.build._module_exists",
                   side_effect=lambda name: name == "pkg_resources"):
            with self.assertRaisesRegex(RuntimeError, "jaraco.text"):
                validate_legacy_pkg_resources()

    def test_doctor_can_offer_jaraco_repair(self):
        from vela.cli.build import LEGACY_PKG_RESOURCES_MODULES
        missing = [Check("Build: " + name, "missing", "")
                   for name in LEGACY_PKG_RESOURCES_MODULES]
        packages = missing_pip_packages(missing)
        self.assertIn("setuptools>=77,<82", packages)
        self.assertIn("jaraco.text>=3.12", packages)
        self.assertIn("more-itertools>=10", packages)
        self.assertEqual(len(packages), len(set(packages)))

    def test_icon_must_exist(self):
        with self.assertRaises(FileNotFoundError):
            build_plan(self.root, BuildOptions(icon="missing.png"))

    def test_workflow_generator_refuses_to_overwrite(self):
        file = generate_workflow(self.root)
        self.assertTrue(file.is_file())
        self.assertIn("ubuntu-22.04", file.read_text())
        self.assertIn("windows-latest", file.read_text())
        with self.assertRaises(FileExistsError):
            generate_workflow(self.root)
        generate_workflow(self.root, force=True)

    def test_desktop_install_and_uninstall_is_isolated_to_test_home(self):
        bundle = self.root / "bundle"
        bundle.mkdir()
        (bundle / "Teste-Vela").write_text("#!/bin/sh\nexit 0\n")
        (bundle / ".vela-app.json").write_text(json.dumps({
            "name": "Teste Vela", "slug": "Teste-Vela", "version": "0.2.0",
            "executable": "Teste-Vela", "file_extensions": [".dfd.json"],
            "description": "Diagrama de dados",
        }))
        datahome = self.root / "fake-local-share"
        with patch.dict(os.environ, {"XDG_DATA_HOME": str(datahome)}):
            with patch("vela.cli.install.platform.system", return_value="Linux"):
                target = install_bundle(bundle, notify=lambda _: None)
                self.assertTrue((target / "Teste-Vela").is_file())
                desktop = datahome / "applications/Teste-Vela.desktop"
                self.assertTrue(desktop.is_file())
                self.assertIn("Exec=", desktop.read_text())
                mime = datahome / "mime/packages/Teste-Vela.xml"
                self.assertTrue(mime.is_file())
                uninstall_app("Teste-Vela")
                self.assertFalse(target.exists())
                self.assertFalse(desktop.exists())

    def test_frozen_elevation_relaunches_executable_instead_of_python_m(self):
        from vela.cli.install import _elevate_linux
        with patch("vela.cli.install.shutil.which", return_value="/usr/bin/pkexec"):
            with patch("vela.cli.install.sys.frozen", True, create=True):
                with patch("vela.cli.install.subprocess.run") as run:
                    _elevate_linux(self.root / "bundle")
                    command = run.call_args.args[0]
                    self.assertEqual(command[0], "/usr/bin/pkexec")
                    self.assertEqual(command[1:],
                                     [__import__("sys").executable, "--vela-install",
                                      "--scope=system"])

    def test_source_elevation_uses_python_module(self):
        from vela.cli.install import _elevate_linux
        with patch("vela.cli.install.shutil.which", return_value="/usr/bin/pkexec"):
            with patch("vela.cli.install.sys.frozen", False, create=True):
                with patch("vela.cli.install.subprocess.run") as run:
                    _elevate_linux(self.root)
                    command = run.call_args.args[0]
                    self.assertEqual(command[2:4], ["-m", "vela.cli.install"])
                    self.assertIn("--bundle", command)

    def test_installer_rejects_path_traversal(self):
        from vela.cli.install import safe_slug
        with self.assertRaises(ValueError):
            safe_slug("../../home")
        with self.assertRaises(ValueError):
            safe_slug("with space")

    def test_doctor_respects_refused_consent(self):
        missing = [Check("PyInstaller", "missing", "Ausente")]
        with patch("vela.cli.doctor.platform.system", return_value="Windows"):
            with patch("vela.cli.doctor.subprocess.run") as run:
                remedy(missing, confirm=lambda prompt: "n", notify=lambda _: None)
                run.assert_not_called()

    def test_missing_pip_packages_is_deduplicated(self):
        missing = [Check("PyQt6", "missing", ""), Check("PyQt6.QtWebEngineWidgets",
                   "missing", ""), Check("PyInstaller", "missing", "")]
        pkgs = missing_pip_packages(missing)
        self.assertEqual(len(pkgs), len(set(pkgs)))


if __name__ == "__main__":
    unittest.main()
