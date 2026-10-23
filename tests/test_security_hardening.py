# SPDX-License-Identifier: MPL-2.0
import os
import sys
import tempfile
import unittest
from pathlib import Path

from vela.config import ConfigLoader
from vela.core.api_server import ApiServer
from vela.core.router import Router
from vela.exceptions import ConfigurationError, TemplateError
from vela.template_engine import mark_safe, render_string, render_template


def _view_with_error(params):
    raise RuntimeError('<script>alert("secret")</script> /tmp/private.py')


class TemplateSecurityTests(unittest.TestCase):
    def test_variables_are_escaped_by_default(self):
        payloads = {
            "script": "<script>alert(1)</script>",
            "image": '<img src=x onerror="alert(1)">',
            "quotes": '"single\' & < >',
        }
        html = render_string("{{ script }}|{{ image }}|{{ quotes }}", payloads)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&lt;img", html)
        self.assertIn("&amp;", html)
        self.assertIn("&quot;", html)
        self.assertIn("&#x27;", html)

    def test_loop_values_are_escaped(self):
        html = render_string(
            '{{ for("users") }}<p>{{ item.name }}</p>{{ endfor }}',
            {"users": [{"name": '<img src=x onerror="boom">'}]},
        )
        self.assertNotIn("<img", html)
        self.assertIn("&lt;img", html)

    def test_safe_html_requires_explicit_marker(self):
        html = render_string(
            "<main>{{ content }}</main>",
            {"content": mark_safe("<strong>OK</strong>")},
        )
        self.assertEqual(html, "<main><strong>OK</strong></main>")

    def test_safe_html_in_loop(self):
        html = render_string(
            '{{ for("items") }}{{ item.html }}{{ endfor }}',
            {"items": [{"html": mark_safe("<em>trusted</em>")}]},
        )
        self.assertEqual(html, "<em>trusted</em>")

    def test_template_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "app"
            app.mkdir()
            (root / "outside.html").write_text("secret", encoding="utf-8")
            previous = Path.cwd()
            os.chdir(app)
            try:
                with self.assertRaises(TemplateError):
                    render_template("../outside.html")
            finally:
                os.chdir(previous)

    def test_static_expression_traversal_is_rejected(self):
        with self.assertRaises(TemplateError):
            render_string("{{ static('../secret.txt') }}")

    def test_template_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "app"
            app.mkdir()
            outside = root / "outside.html"
            outside.write_text("secret", encoding="utf-8")
            link = app / "link.html"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlink não disponível neste ambiente")
            previous = Path.cwd()
            os.chdir(app)
            try:
                with self.assertRaises(TemplateError):
                    render_template("link.html")
            finally:
                os.chdir(previous)


class InternalPageSecurityTests(unittest.TestCase):
    def test_not_found_escapes_path(self):
        router = Router()
        result = router.resolve('/<img src=x onerror="alert(1)">')
        self.assertFalse(result.ok)
        self.assertEqual(result.status, 404)
        self.assertNotIn("<img", result.html)
        self.assertIn("&lt;img", result.html)

    def test_production_error_hides_exception_details(self):
        router = Router()
        router.debug = False
        router.add("/boom", _view_with_error)
        result = router.resolve("/boom")
        self.assertFalse(result.ok)
        self.assertEqual(result.status, 500)
        self.assertIsNotNone(result.error_id)
        self.assertNotIn("private.py", result.html)
        self.assertNotIn("alert", result.html)
        self.assertIn("Erro interno", result.html)

    def test_debug_error_is_escaped(self):
        router = Router()
        router.debug = True
        router.add("/boom", _view_with_error)
        result = router.resolve("/boom")
        self.assertNotIn("<script>", result.html)
        self.assertIn("&lt;script&gt;", result.html)

    def test_static_traversal_is_rejected(self):
        root = Path.cwd().resolve()
        with self.assertRaises(ValueError):
            ApiServer._safe_static_target(root, "../secret")
        with self.assertRaises(ValueError):
            ApiServer._safe_static_target(root, "/etc/passwd")

    def test_static_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "static"
            root.mkdir()
            outside = base / "secret.txt"
            outside.write_text("secret", encoding="utf-8")
            link = root / "escape.txt"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlink não disponível neste ambiente")
            with self.assertRaises(ValueError):
                ApiServer._safe_static_target(root, "escape.txt")


class DynamicImportSecurityTests(unittest.TestCase):
    def test_missing_settings_module_uses_defaults(self):
        loader = ConfigLoader("definitely_missing_vela_settings")
        self.assertIsNone(loader.load_module())

    def test_missing_dependency_inside_settings_is_not_masked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "cfgbroken"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "settings.py").write_text(
                "import dependency_that_does_not_exist_12345\n", encoding="utf-8"
            )
            sys.path.insert(0, directory)
            try:
                with self.assertRaises(ModuleNotFoundError) as caught:
                    ConfigLoader("cfgbroken.settings").load_module()
                self.assertEqual(
                    caught.exception.name, "dependency_that_does_not_exist_12345"
                )
            finally:
                sys.path.remove(directory)
                for name in tuple(sys.modules):
                    if name == "cfgbroken" or name.startswith("cfgbroken."):
                        sys.modules.pop(name, None)

    def test_missing_dependency_inside_app_views_is_not_masked(self):
        from vela.core.app import VelaApp

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "brokenapp"
            views = package / "views"
            views.mkdir(parents=True)
            (package / "__init__.py").write_text("", encoding="utf-8")
            (views / "__init__.py").write_text(
                "import missing_dependency_inside_views_98765\n", encoding="utf-8"
            )
            sys.path.insert(0, directory)
            try:
                app = VelaApp(
                    enable_api=False, settings_module="missing_settings_for_test"
                )
                with self.assertRaises(ModuleNotFoundError) as caught:
                    app.register_app("brokenapp")
                self.assertEqual(
                    caught.exception.name, "missing_dependency_inside_views_98765"
                )
            finally:
                sys.path.remove(directory)
                for name in tuple(sys.modules):
                    if name == "brokenapp" or name.startswith("brokenapp."):
                        sys.modules.pop(name, None)

    def test_remote_api_requires_explicit_opt_in(self):
        from vela.core.api_router import ApiRouter

        with self.assertRaises(ConfigurationError):
            ApiServer(ApiRouter(), host="0.0.0.0", port=8000)
        server = ApiServer(
            ApiRouter(), host="0.0.0.0", port=8000, allow_remote=True
        )
        self.assertTrue(server.allow_remote)


if __name__ == "__main__":
    unittest.main()
