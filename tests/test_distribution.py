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
        self.assertFalse((self.root / ".vela-build").exists())
        self.assertFalse((self.root / "staticfiles").exists())

    def test_launcher_contains_qt_and_system_install_switch(self):
        s = launcher_source("qt6")
        compile(s, "__vela_launcher__.py", "exec")
        self.assertIn("QT_XCB_GL_INTEGRATION", s)
        self.assertIn("--vela-install", s)
        self.assertNotIn("sudo", s)

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
