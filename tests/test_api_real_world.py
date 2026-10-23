# SPDX-License-Identifier: MPL-2.0
import io
import json
import socket
import unittest
from wsgiref.util import setup_testing_defaults

from bottle import BaseRequest

from vela.core.api_router import ApiRouter
from vela.core.api_server import ApiServer
from vela.core.http import Request
from vela.exceptions import ConfigurationError


def wsgi_request(app, path, method="GET", body=b"", content_type="application/json"):
    env = {}; setup_testing_defaults(env)
    env.update(REQUEST_METHOD=method, PATH_INFO=path, CONTENT_LENGTH=str(len(body)), CONTENT_TYPE=content_type, **{"wsgi.input": io.BytesIO(body)})
    statuses = []
    def start_response(status, headers, exc_info=None): statuses.append(status)
    data = b"".join(app(env, start_response))
    return statuses[0], data


class ApiPrefixRegressionTests(unittest.TestCase):
    def test_app_route_must_not_repeat_framework_prefix(self):
        router = ApiRouter(); router.get("/api/devices")(lambda: {})
        with self.assertRaisesRegex(ConfigurationError, "já contém o prefixo"):
            ApiServer(router, prefix="/api")

    def test_normal_route_gets_prefix_once(self):
        router = ApiRouter(); router.get("/devices")(lambda: {"ok": True})
        server = ApiServer(router, prefix="/api"); server.register_routes()
        status, _ = wsgi_request(server.app, "/api/devices")
        self.assertTrue(status.startswith("200"))
        status, _ = wsgi_request(server.app, "/api/api/devices")
        self.assertTrue(status.startswith("404"))

    def test_head_patch_delete_and_options_are_supported(self):
        router = ApiRouter()
        for method in ("HEAD", "PATCH", "DELETE", "OPTIONS"):
            router.add_route(method, f"/{method.lower()}", lambda: {"ok": True})
        self.assertEqual({r.method for r in router.routes}, {"HEAD", "PATCH", "DELETE", "OPTIONS"})

    def test_route_parameters_are_available_on_request(self):
        router = ApiRouter()
        def device(request: Request): return {"device": request.path_params["device_id"]}
        router.get("/devices/<device_id>")(device)
        server = ApiServer(router); server.register_routes()
        status, body = wsgi_request(server.app, "/api/devices/abc-123")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(json.loads(body)["device"], "abc-123")


class LargeBodyRegressionTests(unittest.TestCase):
    def test_configured_large_body_works_without_consumer_bottle_patch(self):
        router = ApiRouter(); router.post("/doc")(lambda data: {"size": len(data["text"])})
        limit = 2 * 1024 * 1024
        server = ApiServer(router, max_body_size=limit); server.register_routes()
        payload = json.dumps({"text": "x" * (512 * 1024)}).encode()
        status, body = wsgi_request(server.app, "/api/doc", "POST", payload)
        self.assertTrue(status.startswith("200"))
        self.assertEqual(json.loads(body)["size"], 512 * 1024)
        self.assertGreaterEqual(BaseRequest.MEMFILE_MAX, limit)

    def test_body_above_configured_limit_is_413(self):
        router = ApiRouter(); router.post("/doc")(lambda data: {"ok": True})
        server = ApiServer(router, max_body_size=1024); server.register_routes()
        payload = json.dumps({"text": "x" * 2048}).encode()
        status, body = wsgi_request(server.app, "/api/doc", "POST", payload)
        self.assertTrue(status.startswith("413"))
        self.assertEqual(json.loads(body)["error"]["code"], "payload_too_large")


class ServerShutdownRegressionTests(unittest.TestCase):
    def test_bottle_backend_stop_releases_bound_port(self):
        server = ApiServer(ApiRouter(), port=0, server="bottle")
        port = server.start(); server.wait_until_ready(timeout=2)
        server.stop(); server.stop()
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            probe.bind(("127.0.0.1", port))
        finally:
            probe.close()


if __name__ == "__main__": unittest.main()
