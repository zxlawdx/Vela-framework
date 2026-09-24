# SPDX-License-Identifier: MPL-2.0
"""Contratos da API/documentacao e regressoes de desempenho sem rede."""
import inspect
import io
import json
import unittest
from unittest.mock import patch

from wsgiref.util import setup_testing_defaults
from vela.core.api_router import ApiRouter
from vela.core.api_server import ApiServer
from vela.core.api_docs import build_openapi
from vela.core.bridge import BaseBridge
from vela.core.router import Router


def handle(data):
    """Echo da requisicao."""
    return {"echo": data.get("hello")}


def view(params):
    return "<h1>OK</h1>"


def wsgi_request(app, url, method="GET", data=None):
    env = {}
    setup_testing_defaults(env)
    body = json.dumps(data).encode() if data is not None else b""
    env.update(REQUEST_METHOD=method, PATH_INFO=url, CONTENT_LENGTH=str(len(body)),
               CONTENT_TYPE="application/json", **{"wsgi.input": io.BytesIO(body)})
    status = []
    def start_response(line, headers, exc_info=None):
        status.append(line)
    response = b"".join(app(env, start_response))
    return status[0], response


class ApiFeatures(unittest.TestCase):
    def setUp(self):
        self.routes = ApiRouter()
        self.routes.post("/echo")(handle)
        self.server = ApiServer(self.routes, port=0, docs_enabled=True)
        self.server.register_routes()

    def test_openapi_and_health(self):
        status, body = wsgi_request(self.server.app, "/api/openapi.json")
        self.assertTrue(status.startswith("200"))
        spec = json.loads(body)
        self.assertIn("/api/echo", spec["paths"])
        self.assertEqual(spec["paths"]["/api/echo"]["post"]["summary"],
                         "Echo da requisicao.")
        status, body = wsgi_request(self.server.app, "/api/health")
        self.assertTrue(status.startswith("200"))
        self.assertTrue(json.loads(body)["ok"])

    def test_docs_are_bundled_offline(self):
        status, body = wsgi_request(self.server.app, "/api/docs")
        self.assertTrue(status.startswith("200"))
        self.assertIn(b"/api/openapi.json", body)
        self.assertNotIn(b"cdn.", body)

    def test_local_css_replaces_external_shell_cdn(self):
        import os
        import tempfile
        from pathlib import Path
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "staticfiles/css").mkdir(parents=True)
            (root / "staticfiles/css/vela.bundle.css").write_text("/* offline */")
            os.chdir(root)
            try:
                status, body = wsgi_request(self.server.app, "/__vela__/shell")
                self.assertTrue(status.startswith("200"))
                self.assertIn(b"static/css/vela.bundle.css", body)
                self.assertNotIn(b"https://cdn.tailwindcss.com", body)
                self.assertNotIn(b"tailwind.config", body)
            finally:
                os.chdir(previous)

    def test_docs_can_be_disabled_without_disabling_schema(self):
        disabled = ApiServer(self.routes, port=0, docs_enabled=False)
        status, _ = wsgi_request(disabled.app, "/api/docs")
        self.assertTrue(status.startswith("404"))
        status, _ = wsgi_request(disabled.app, "/api/openapi.json")
        self.assertTrue(status.startswith("200"))

    def test_handler_signature_is_cached_across_requests(self):
        # Na versao antiga inspect.signature era executado em cada requisicao.
        with patch("vela.core.api_server.inspect.signature",
                   wraps=inspect.signature) as signature:
            server = ApiServer(self.routes, port=0)
            server.register_routes()
            calls_after_register = signature.call_count
            for i in range(12):
                status, body = wsgi_request(server.app, "/api/echo",
                                            "POST", {"hello": i})
                self.assertTrue(status.startswith("200"))
                self.assertEqual(json.loads(body)["echo"], i)
            self.assertEqual(signature.call_count, calls_after_register)

    def test_duplicate_route_registration_replaces_handler(self):
        router = ApiRouter()
        router.get("/healthz")(lambda: {"ok": 1})
        router.get("/healthz")(lambda: {"ok": 2})
        self.assertEqual(len(router.routes), 1)

    def test_no_production_reload(self):
        router = Router()
        router.add("/home", view)
        self.assertFalse(router.debug)
        with patch("vela.core.router.importlib.reload",
                   side_effect=AssertionError("recarregou em producao")):
            page = router.resolve("/home")
        self.assertIn("OK", page["html"])

    def test_frozen_production_mode_disables_dev_reload(self):
        from vela.core.app import VelaApp
        with patch.dict("os.environ", {"VELA_PRODUCTION": "1"}):
            app = VelaApp(enable_api=False)
        self.assertFalse(app._config["debug"])
        self.assertFalse(app.router.debug)
        self.assertFalse(app.bridge.config["debug"])

    def test_bridge_does_not_reload_production_modules(self):
        router = Router()
        router.add("/home", view)
        bridge = BaseBridge(router=router, config={"debug": False})
        with patch.object(bridge, "_reload_app_modules",
                          side_effect=AssertionError("reload inesperado")):
            self.assertTrue(bridge.navigate("/home")["ok"])


if __name__ == "__main__":
    unittest.main()
