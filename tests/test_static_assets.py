# SPDX-License-Identifier: MPL-2.0
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vela.cli import collectstatic
from vela.cli.tools import executable_candidates, resolve_node_tool
from vela.static import AssetManifest, StaticResolver
from vela.template_engine import render_string


class StaticResolverTests(unittest.TestCase):
    def test_runtime_url_is_stable_and_encoded(self):
        resolver = StaticResolver.for_project(".")
        self.assertEqual(resolver.url("css/app file.css"), "/__vela__/static/css/app%20file.css")
        self.assertEqual(
            resolver.url("js/app.js", base_url="http://127.0.0.1:9000/"),
            "http://127.0.0.1:9000/__vela__/static/js/app.js",
        )

    def test_template_static_uses_same_contract(self):
        html = render_string(
            "{{ static('css/app.css') }}",
            {"__base_url__": "http://127.0.0.1:8000"},
        )
        self.assertEqual(html, "http://127.0.0.1:8000/__vela__/static/css/app.css")

    def test_traversal_and_absolute_paths_are_rejected(self):
        resolver = StaticResolver.for_project(".")
        for value in ("../secret", "../../secret", "/etc/passwd", "C:\\Windows\\x"):
            with self.assertRaises(ValueError, msg=value):
                resolver.url(value)

    def test_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            collected = root / "staticfiles"
            collected.mkdir()
            outside = root / "secret.txt"
            outside.write_text("secret", encoding="utf-8")
            link = collected / "escape.txt"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlink indisponível")
            resolver = StaticResolver.for_project(root)
            with self.assertRaises(ValueError):
                resolver.resolve_collected("escape.txt")

    def test_manifest_uses_sha256_and_detects_stale_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.js").write_text("one", encoding="utf-8")
            manifest = AssetManifest.generate(root)
            manifest.write()
            self.assertEqual(manifest.algorithm, "sha256")
            self.assertEqual(manifest.verify(["app.js"]), [])
            (root / "app.js").write_text("two", encoding="utf-8")
            self.assertEqual(manifest.verify(["app.js"]), ["hash divergente: app.js"])


class PortableNodeToolTests(unittest.TestCase):
    def test_windows_candidates_prefer_cmd_and_never_local_posix_shim(self):
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory) / "node_modules" / ".bin"
            local.mkdir(parents=True)
            (local / "npx").write_text("#!/bin/sh", encoding="utf-8")
            (local / "npx.cmd").write_text("@echo off", encoding="utf-8")
            with mock.patch("vela.cli.tools.shutil.which", return_value=None):
                candidates = executable_candidates(
                    "npx", project_root=directory, platform_name="win32"
                )
                self.assertTrue(candidates[0].endswith("npx.cmd"))
                self.assertFalse(any(Path(item).name == "npx" for item in candidates))
                self.assertTrue(
                    resolve_node_tool("npx", project_root=directory, platform_name="win32").endswith("npx.cmd")
                )

    def test_posix_candidates_use_executable_shim(self):
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory) / "node_modules" / ".bin"
            local.mkdir(parents=True)
            shim = local / "npx"
            shim.write_text("#!/bin/sh\n", encoding="utf-8")
            shim.chmod(0o755)
            with mock.patch("vela.cli.tools.shutil.which", return_value=None):
                self.assertEqual(
                    resolve_node_tool("npx", project_root=directory, platform_name="linux"),
                    str(shim),
                )

    def test_collectstatic_subprocess_never_uses_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            css = project / "input.css"
            css.write_text("", encoding="utf-8")
            output = project / "out.css"
            fake = project / "tailwindcss.cmd"
            fake.write_text("", encoding="utf-8")
            completed = mock.Mock(returncode=0, stderr="")
            with mock.patch("vela.cli.collectstatic.resolve_node_tool", return_value=str(fake)), mock.patch(
                "vela.cli.collectstatic.subprocess.run", return_value=completed
            ) as run:
                with mock.patch.object(Path, "stat") as stat:
                    stat.return_value.st_size = 0
                    self.assertTrue(
                        collectstatic._compile_tailwind(
                            directory, str(css), str(output), False, False
                        )
                    )
                self.assertIs(run.call_args.kwargs["shell"], False)


class CollectStaticManifestTests(unittest.TestCase):
    def test_collectstatic_keeps_collected_static_separate_from_build_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app_static = root / "apps" / "demo" / "static" / "js"
            app_static.mkdir(parents=True)
            (app_static / "app.js").write_text("console.log('ok')", encoding="utf-8")
            previous = Path.cwd()
            os.chdir(root)
            try:
                result = collectstatic.collect_static(skip_tailwind=True, verbose=False)
            finally:
                os.chdir(previous)
            self.assertTrue((root / "staticfiles" / "demo" / "js" / "app.js").is_file())
            self.assertFalse((root / ".vela-build").exists())
            data = json.loads((root / "staticfiles" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(data["algorithm"], "sha256")
            self.assertEqual(result["errors"], 0)


if __name__ == "__main__":
    unittest.main()
