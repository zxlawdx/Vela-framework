# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from vela.cli import asset_pipeline, collectstatic


class AssetPipelineTests(unittest.TestCase):
    def test_missing_node_is_actionable_and_never_installs_system_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text("{}", encoding="utf-8")
            with mock.patch(
                "vela.cli.asset_pipeline.resolve_node_tool", return_value=None
            ):
                with self.assertRaises(asset_pipeline.AssetPipelineError) as raised:
                    asset_pipeline.run_project_asset_pipeline(
                        root,
                        {"node": {"scripts": ["build:vendor"]}},
                        assume_yes=True,
                        verbose=False,
                    )
            message = str(raised.exception)
            self.assertIn("Instale Node.js", message)
            self.assertIn("collectstatic", message)
            self.assertIn("não instala pacotes de sistema", message)

    def test_noninteractive_missing_dependencies_require_explicit_yes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text("{}", encoding="utf-8")
            (root / "package-lock.json").write_text("{}", encoding="utf-8")
            with (
                mock.patch(
                    "vela.cli.asset_pipeline._node_tools",
                    return_value=("/usr/bin/node", "/usr/bin/npm"),
                ),
                mock.patch(
                    "vela.cli.asset_pipeline._node_dependencies_ready", return_value=False
                ),
                mock.patch.object(sys.stdin, "isatty", return_value=False),
            ):
                with self.assertRaises(asset_pipeline.AssetPipelineError) as raised:
                    asset_pipeline.run_project_asset_pipeline(
                        root,
                        {"node": {"install": "ci"}},
                        verbose=False,
                    )
            self.assertIn("collectstatic --yes", str(raised.exception))

    def test_yes_installs_local_dependencies_then_runs_scripts_and_hooks(self):
        hook_module = types.ModuleType("vela_test_asset_hook")
        calls: list[str] = []
        hook_module.build = lambda: calls.append("hook")
        sys.modules[hook_module.__name__] = hook_module
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "package.json").write_text("{}", encoding="utf-8")
                (root / "package-lock.json").write_text("{}", encoding="utf-8")
                completed = mock.Mock(returncode=0)
                with (
                    mock.patch(
                        "vela.cli.asset_pipeline._node_tools",
                        return_value=("/usr/bin/node", "/usr/bin/npm"),
                    ),
                    mock.patch(
                        "vela.cli.asset_pipeline._node_dependencies_ready", return_value=False
                    ),
                    mock.patch(
                        "vela.cli.asset_pipeline._run", return_value=completed
                    ) as run,
                ):
                    report = asset_pipeline.run_project_asset_pipeline(
                        root,
                        {
                            "node": {
                                "install": "ci",
                                "scripts": ["build:vendor"],
                            },
                            "hooks": ["vela_test_asset_hook:build"],
                        },
                        assume_yes=True,
                        verbose=False,
                    )
                commands = [call.args[0] for call in run.call_args_list]
                self.assertIn(["/usr/bin/npm", "ci"], commands)
                self.assertIn(["/usr/bin/npm", "run", "build:vendor"], commands)
                self.assertEqual(calls, ["hook"])
                self.assertEqual(report["node_dependencies"], "ci")
                self.assertEqual(report["npm_scripts"], ["build:vendor"])
        finally:
            sys.modules.pop(hook_module.__name__, None)

    def test_python_hook_runs_before_app_static_copy(self):
        hook_module = types.ModuleType("vela_test_collect_hook")
        previous = Path.cwd()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                static = root / "apps" / "demo" / "static"
                static.mkdir(parents=True)

                def build():
                    (static / "generated.css").write_text("generated", encoding="utf-8")

                hook_module.build = build
                sys.modules[hook_module.__name__] = hook_module
                os.chdir(root)
                result = collectstatic.collect_static(
                    verbose=False,
                    asset_config={
                        "hooks": ["vela_test_collect_hook:build"],
                        "tailwind": False,
                    },
                )
                self.assertTrue(
                    (root / "staticfiles" / "demo" / "generated.css").is_file()
                )
                self.assertFalse(result["tailwind_bundle"])
                self.assertEqual(
                    result["asset_pipeline"]["python_hooks"],
                    ["vela_test_collect_hook:build"],
                )
        finally:
            os.chdir(previous)
            sys.modules.pop(hook_module.__name__, None)


if __name__ == "__main__":
    unittest.main()
