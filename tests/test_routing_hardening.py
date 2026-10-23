# SPDX-License-Identifier: MPL-2.0
import io
import json
import unittest
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from uuid import UUID
from wsgiref.util import setup_testing_defaults

from vela.api import ApiFacade
from vela.core.api_router import ApiRouter
from vela.core.api_server import ApiServer
from vela.core.http import Request, Response, ResponseEncoder
from vela.core.router import Router
from vela.exceptions import ConfigurationError


def wsgi_request(app, url, method="GET", data=None, raw=None, content_type="application/json"):
    env = {}
    setup_testing_defaults(env)
    body = raw if raw is not None else json.dumps(data).encode() if data is not None else b""
    env.update(
        REQUEST_METHOD=method,
        PATH_INFO=url,
        CONTENT_LENGTH=str(len(body)),
        CONTENT_TYPE=content_type,
        **{"wsgi.input": io.BytesIO(body)},
    )
    status = []
    headers = []

    def start_response(line, response_headers, exc_info=None):
        status.append(line)
        headers.extend(response_headers)

    content = b"".join(app(env, start_response))
    return status[0], dict(headers), content


class PublicApiCompatibilityTests(unittest.TestCase):
    def test_vela_app_is_exported_from_package_root(self):
        from vela import VelaApp
        from vela.core.app import VelaApp as CoreVelaApp

        self.assertIs(VelaApp, CoreVelaApp)


class ApiRouterTests(unittest.TestCase):
    def test_methods_duplicate_replacement_and_order(self):
        router = ApiRouter()
        for method in ("GET", "POST", "PUT", "DELETE"):

            def handler(method=method):
                return {"method": method}

            router.add_route(method, "/items", handler)
        self.assertEqual(
            [route.method for route in router.routes],
            ["GET", "POST", "PUT", "DELETE"],
        )

        def replacement():
            return {"new": True}

        router.add_route("GET", "/items", replacement)
        self.assertEqual(len(router.routes), 4)
        self.assertIs(router.get_route("GET", "/items").handler, replacement)
        self.assertEqual(
            [route.method for route in router.routes],
            ["GET", "POST", "PUT", "DELETE"],
        )

    def test_many_routes_use_keyed_registry(self):
        router = ApiRouter()
        for index in range(1000):
            router.get(f"/route-{index}")(lambda index=index: index)
        self.assertEqual(len(router.routes), 1000)
        self.assertIsNotNone(router.get_route("GET", "/route-999"))
        self.assertIsInstance(router._routes, dict)

    def test_api_facade_isolates_bound_registries(self):
        facade = ApiFacade()
        app_a = facade.new_router()
        app_b = facade.new_router()
        with facade.bind(app_a):
            facade.get("/only-a")(lambda: {"app": "a"})
        self.assertIsNotNone(app_a.get_route("GET", "/only-a"))
        self.assertIsNone(app_b.get_route("GET", "/only-a"))


class PageRouterTests(unittest.TestCase):
    def test_duplicate_path_conflict_is_explicit(self):
        router = Router()
        router.add("/x", lambda params: "a", name="x")
        with self.assertRaises(ConfigurationError):
            router.add("/x", lambda params: "b", name="x")

    def test_sidebar_cache_invalidates_on_add(self):
        router = Router()
        router.add("/a", lambda params: "a", title="A", order=2)
        first = router.get_sidebar_routes()
        self.assertEqual([route["path"] for route in first], ["/a"])
        router.add("/b", lambda params: "b", title="B", order=1)
        second = router.get_sidebar_routes()
        self.assertEqual([route["path"] for route in second], ["/b", "/a"])


class HttpContractTests(unittest.TestCase):
    def test_typed_request_binding(self):
        router = ApiRouter()

        @router.post("/typed")
        def typed(request: Request):
            return {"method": request.method, "name": request.json["name"]}

        server = ApiServer(router, port=0)
        server.register_routes()
        status, _, body = wsgi_request(server.app, "/api/typed", "POST", {"name": "Vela"})
        self.assertTrue(status.startswith("200"))
        self.assertEqual(json.loads(body), {"method": "POST", "name": "Vela"})

    def test_legacy_context_and_data_still_work(self):
        router = ApiRouter()

        @router.post("/context")
        def legacy_context(context):
            return {"path": context["path"], "value": context["json"]["x"]}

        @router.post("/data")
        def legacy_data(data):
            return {"value": data["x"]}

        server = ApiServer(router, port=0)
        server.register_routes()
        for path in ("/api/context", "/api/data"):
            status, _, body = wsgi_request(server.app, path, "POST", {"x": 7})
            self.assertTrue(status.startswith("200"))
            self.assertEqual(json.loads(body)["value"], 7)

    def test_invalid_json_is_400(self):
        router = ApiRouter()
        router.post("/x")(lambda data: data)
        server = ApiServer(router, port=0)
        server.register_routes()
        status, _, body = wsgi_request(server.app, "/api/x", "POST", raw=b"{broken")
        self.assertTrue(status.startswith("400"))
        payload = json.loads(body)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "invalid_request")

    def test_request_body_limit_is_413(self):
        router = ApiRouter()
        router.post("/x")(lambda data: data)
        server = ApiServer(router, port=0, max_body_size=8)
        server.register_routes()
        status, _, body = wsgi_request(server.app, "/api/x", "POST", raw=b'{"long":"payload"}')
        self.assertTrue(status.startswith("413"))
        self.assertEqual(json.loads(body)["error"]["code"], "payload_too_large")

    def test_internal_exception_is_redacted_in_production(self):
        router = ApiRouter()

        @router.get("/boom")
        def boom():
            raise RuntimeError("password=/tmp/secret")

        server = ApiServer(router, port=0, debug=False)
        server.register_routes()
        status, _, body = wsgi_request(server.app, "/api/boom")
        self.assertTrue(status.startswith("500"))
        text = body.decode()
        self.assertNotIn("password", text)
        self.assertIn("VELA-E-", text)

    def test_explicit_response_contract(self):
        router = ApiRouter()
        router.get("/created")(lambda: Response({"ok": True}, status=201, headers={"X-Test": "1"}))
        server = ApiServer(router, port=0)
        server.register_routes()
        status, headers, body = wsgi_request(server.app, "/api/created")
        self.assertTrue(status.startswith("201"))
        self.assertEqual(headers["X-Test"], "1")
        self.assertTrue(json.loads(body)["ok"])

    def test_response_encoder_supported_types(self):
        class Kind(Enum):
            A = "a"

        @dataclass
        class Payload:
            when: date
            kind: Kind

        value = {
            "payload": Payload(date(2026, 10, 23), Kind.A),
            "uuid": UUID("12345678-1234-5678-1234-567812345678"),
            "tuple": (1, 2),
            "datetime": datetime(2026, 10, 23, 12, 30),
        }
        encoded = ResponseEncoder.to_jsonable(value)
        self.assertEqual(encoded["payload"]["when"], "2026-10-23")
        self.assertEqual(encoded["payload"]["kind"], "a")
        self.assertEqual(encoded["tuple"], [1, 2])


if __name__ == "__main__":
    unittest.main()
