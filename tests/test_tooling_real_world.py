# SPDX-License-Identifier: MPL-2.0
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vela.cli.assets import verify_assets
from vela.cli.build_report import build_report
from vela.cli.doctor import diagnose
from vela.cli.collectstatic import collect_static


class AssetVerificationTests(unittest.TestCase):
    def test_offline_assets_are_verified_and_missing_source_is_explained(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "apps" / "demo" / "static"
            source.mkdir(parents=True)
            (source / "app.js").write_text("ok", encoding="utf-8")
            previous = Path.cwd(); os.chdir(root)
            try:
                collect_static(skip_tailwind=True, verbose=False)
                result = verify_assets(root)
            finally:
                os.chdir(previous)
            self.assertTrue(result.ok, result.errors)
            (root / "staticfiles" / "demo" / "app.js").unlink()
            result = verify_assets(root)
            self.assertFalse(result.ok)
            self.assertTrue(any("não encontrado" in error or "ausente" in error for error in result.errors))


class DoctorRegressionTests(unittest.TestCase):
    def test_doctor_warns_when_active_venv_belongs_to_another_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"; root.mkdir(); (root / "manage.py").write_text("")
            other = Path(directory) / "other" / ".venv"; other.mkdir(parents=True)
            with mock.patch("vela.cli.doctor._active_venv", return_value=other):
                checks = diagnose(root=root, backend="native")
            venv = next(item for item in checks if item.name == "VENV_ROOT")
            self.assertEqual(venv.status, "warning")
            self.assertIn("does not belong to current project", venv.hint)

    def test_doctor_reports_incomplete_framework_component(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch(
            "vela.cli.doctor._module_exists", side_effect=lambda name: name != "vela.cli.commands"
        ):
            checks = diagnose(root=directory, backend="native")
        broken = next(item for item in checks if item.name == "Framework: vela.cli.commands")
        self.assertEqual(broken.status, "missing")


class BuildReportTests(unittest.TestCase):
    def test_build_report_contains_required_contract_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "apps" / "demo").mkdir(parents=True); (root / "apps" / "demo" / "__init__.py").write_text("")
            report = build_report({"gui": "qt6", "hidden_imports": ["apps.demo.api"]}, root)
        for field in ("python", "vela", "platform", "backend", "apps", "hidden_imports", "assets", "entrypoint", "warnings"):
            self.assertIn(field, report)
        self.assertEqual(report["apps"], ["demo"])


if __name__ == "__main__": unittest.main()
