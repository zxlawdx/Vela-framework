# SPDX-License-Identifier: MPL-2.0
"""OpenAPI generation from the existing per-application API registry."""

from __future__ import annotations

import inspect
import re
import types
from copy import deepcopy
from typing import Any, Literal, Union, get_args, get_origin

from vela.core.http import Request, Response


def _schema(annotation: Any) -> dict:
    if annotation in (inspect.Signature.empty, Any, Request, Response):
        return {}
    if annotation is None or annotation is type(None):
        return {"nullable": True}
    if hasattr(annotation, "model_json_schema"):
        schema = deepcopy(annotation.model_json_schema(ref_template="#/components/schemas/{model}"))
        return schema
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (Union, types.UnionType):
        choices = [_schema(a) for a in args if a is not type(None)]
        schema = choices[0] if len(choices) == 1 else {"anyOf": choices}
        return {**schema, **({"nullable": True} if type(None) in args else {})}
    if origin is Literal:
        return {"enum": list(args), **(_schema(type(args[0])) if args else {})}
    if origin in (list, tuple, set):
        return {"type": "array", "items": _schema(args[0]) if args else {}}
    if origin is dict:
        return {"type": "object", "additionalProperties": _schema(args[1]) if len(args) > 1 else {}}
    return {
        str: {"type": "string"},
        int: {"type": "integer"},
        bool: {"type": "boolean"},
        float: {"type": "number"},
        dict: {"type": "object"},
        list: {"type": "array", "items": {}},
    }.get(annotation, {})


def _register_schema(annotation: Any, components: dict) -> dict:
    schema = _schema(annotation)

    def collect(node):
        if isinstance(node, dict):
            definitions = node.pop("$defs", {})
            for name, definition in definitions.items():
                collect(definition)
                components[name] = definition
            for value in node.values():
                collect(value)
        elif isinstance(node, list):
            for value in node:
                collect(value)

    collect(schema)
    if hasattr(annotation, "model_json_schema"):
        name = annotation.__name__
        components[name] = schema
        return {"$ref": f"#/components/schemas/{name}"}
    return schema


def build_openapi(routes, prefix="/api", *, title=None, version=None):
    import vela

    spec = {
        "openapi": "3.0.3",
        "info": {"title": title or "Vela Local API", "version": version or vela.__version__},
        "servers": [{"url": "/"}],
        "paths": {},
        "components": {"schemas": {}},
    }
    components = spec["components"]["schemas"]
    used_ids = set()
    for route in routes:
        # Bottle is the routing source of truth; do not invent a second router.
        path = re.sub(r"<([A-Za-z_]\w*)(?::[^>]*)?>", r"{\1}", prefix + route.path)
        handler = route.handler
        doc = inspect.getdoc(handler) or ""
        name = getattr(handler, "__name__", "handler")
        metadata = deepcopy(getattr(handler, "__vela_openapi__", {}))
        op_id = metadata.get("operationId", name)
        if op_id in used_ids:
            op_id = f"{op_id}_{route.method.lower()}_{len(used_ids)}"
        used_ids.add(op_id)
        operation = {
            "summary": doc.splitlines()[0] if doc else name,
            "description": doc,
            "operationId": op_id,
            "tags": [route.path.strip("/").split("/")[0] or "API"],
            "responses": {
                "200": {"description": "Sucesso"},
                "400": {"description": "Requisição inválida"},
                "422": {"description": "Falha de validação"},
                "500": {"description": "Erro interno"},
            },
        }
        path_params = []
        for match in re.finditer(r"<([A-Za-z_]\w*)(?::([^>]*))?>", route.path):
            kind = {"int": "integer", "float": "number"}.get(match[2], "string")
            path_params.append(
                {"name": match[1], "in": "path", "required": True, "schema": {"type": kind}}
            )
        if path_params:
            operation["parameters"] = path_params
        params = list(route.signature.parameters.values())
        if route.method in {"POST", "PUT", "PATCH"} and params:
            first = params[0]
            annotation = route.type_hints.get(first.name, first.annotation)
            if annotation is not Request:
                operation["requestBody"] = {
                    "required": hasattr(annotation, "model_validate"),
                    "content": {
                        "application/json": {"schema": _register_schema(annotation, components)}
                    },
                }
        annotation = route.type_hints.get("return", route.signature.return_annotation)
        result_schema = _register_schema(annotation, components)
        if result_schema:
            operation["responses"]["200"]["content"] = {
                "application/json": {"schema": result_schema}
            }
        operation.update(metadata)
        operation["operationId"] = op_id
        # Always retain path parameters even when explicit query/header metadata is supplied.
        explicit = operation.get("parameters", [])
        operation["parameters"] = [
            p
            for p in path_params
            if not any(q.get("name") == p["name"] and q.get("in") == "path" for q in explicit)
        ] + explicit
        spec["paths"].setdefault(path, {})[route.method.lower()] = operation
    return spec
