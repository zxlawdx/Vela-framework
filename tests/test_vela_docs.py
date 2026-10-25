"""Regression tests for the integrated, offline Docs provider."""

import json
from pathlib import Path

import pytest

from tests.test_api_features import wsgi_request
from vela.core.api_docs import build_openapi
from vela.core.api_router import ApiRouter
from vela.core.api_server import ApiServer
from vela.core.http import Request
from vela.docs import documented


def test_metadata_path_parameters_and_real_request():
    router = ApiRouter()

    @router.get("/devices/<id:int>")
    @documented(
        tags=["Devices"],
        parameters=[{"name": "limit", "in": "query", "schema": {"type": "integer"}}],
    )
    def device(request: Request) -> dict:
        """Obter dispositivo.

        Informações do dispositivo registrado.
        """
        return {"id": int(request.path_params["id"])}

    server = ApiServer(router, docs_title="Minha API", docs_version="1.2")
    server.register_routes()
    spec = build_openapi(router.routes, title="Minha API", version="1.2")
    op = spec["paths"]["/api/devices/{id}"]["get"]
    assert op["tags"] == ["Devices"]
    assert op["parameters"][0]["name"] == "id"
    assert op["parameters"][0]["schema"]["type"] == "integer"
    assert op["parameters"][1]["in"] == "query"
    assert spec["info"] == {"title": "Minha API", "version": "1.2"}
    status, body = wsgi_request(server.app, "/api/devices/12")
    assert status.startswith("200") and json.loads(body) == {"id": 12}


def test_postponed_pydantic_body_and_nested_refs():
    BaseModel = pytest.importorskip("pydantic").BaseModel

    class Child(BaseModel):
        value: int

    class Payload(BaseModel):
        child: Child

    Payload.model_rebuild()

    def create(data: Payload) -> Payload:
        return data

    router = ApiRouter()
    router.post("/items")(create)
    spec = build_openapi(router.routes)
    media = spec["paths"]["/api/items"]["post"]["requestBody"]["content"]["application/json"]
    assert media["schema"]["$ref"] == "#/components/schemas/Payload"
    assert "Child" in spec["components"]["schemas"]
    assert (
        spec["components"]["schemas"]["Payload"]["properties"]["child"]["$ref"]
        == "#/components/schemas/Child"
    )


def test_offline_assets_prefix_and_disable():
    server = ApiServer(ApiRouter(), prefix="/local")
    status, html = wsgi_request(server.app, "/local/docs")
    assert status.startswith("200")
    assert b"/local/docs/assets/js/app.js" in html
    assert b"__VELA_" not in html
    assert b"https://" not in html
    for asset in ["css/vela-docs.css", "js/app.js", "js/openapi.js", "js/try_it.js"]:
        status, body = wsgi_request(server.app, "/local/docs/assets/" + asset)
        assert status.startswith("200") and body
    for path in ["/api/docs", "/api/docs/assets/js/app.js"]:
        status, _ = wsgi_request(ApiServer(ApiRouter(), docs_enabled=False).app, path)
        assert status.startswith("404")
    for path in ["/local/docs/assets/../__init__.py", "/local/docs/assets/%2e%2e/api_docs.py"]:
        status, _ = wsgi_request(server.app, path)
        assert status.startswith("404")


def test_empty_missing_description_and_unique_ids():
    assert build_openapi([])["paths"] == {}
    router = ApiRouter()
    router.get("/one")(lambda: {})
    router.get("/two")(lambda: {})
    ops = [v["get"] for v in build_openapi(router.routes)["paths"].values()]
    assert all(op["description"] == "" for op in ops)
    assert len({op["operationId"] for op in ops}) == 2


def test_no_unsafe_html_or_execution_in_docs_modules():
    files = Path("vela/docs/static/js").glob("*.js")
    for path in files:
        source = path.read_text()
        assert "innerHTML" not in source
        assert "eval(" not in source
        assert "new Function" not in source
