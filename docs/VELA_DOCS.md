# Vela Docs

Vela Docs is the offline OpenAPI explorer bundled with the existing Bottle/Waitress
API server. It replaces the previous basic API page; it does not replace the router,
request binder, WebView, or HTTP implementation. No CDN, npm build or FastAPI is needed.

## Enable and run

In the application's `config/settings.py`:

```python
API = {
    "enabled": True,
    "host": "127.0.0.1",
    "port": 8000,
    "prefix": "/api",
    "docs_enabled": True,
    "docs_title": "Meu App API",
    "docs_version": "0.2.0",
}
```

Install this checkout in the application's virtual environment with
`python -m pip install -e /path/to/Vela-framework`, then run the application normally
with `python manage.py runapp`. Open `http://127.0.0.1:8000/api/docs` in a browser.
If auto-port selects another port, use the port reported by Vela. The frontend uses
relative URLs and therefore also works at that port. Change `prefix` to move the
schema, docs and docs assets together. Disabling docs keeps OpenAPI JSON available,
as in previous versions.

## Register and document a route

Vela handlers still receive zero arguments or one Request/model/data argument.
Bottle path syntax is the source of truth: use `<id:int>`, not FastAPI-style `{id}`.
The OpenAPI generator translates that syntax to `{id}` for documentation.

```python
from vela.api import api
from vela.core.http import Request
from vela.docs import documented

@api.get("/devices/<id:int>")
@documented(
    tags=["Devices"],
    parameters=[
        {"name": "id", "in": "path", "required": True,
         "schema": {"type": "integer", "example": 1}},
        {"name": "verbose", "in": "query", "required": False,
         "schema": {"type": "string", "enum": ["yes", "no"]}},
    ],
    responses={
        "200": {"description": "Success", "content": {
            "application/json": {"example": {"id": 1, "status": "online"}}
        }},
        "404": {"description": "Device not found"},
    },
)
def device(request: Request) -> dict:
    """Obter dispositivo.

    Retorna informações detalhadas sobre um dispositivo registrado.
    """
    return {"id": int(request.path_params["id"]), "status": "online"}
```

Keep the API module registered through the application's existing app registration.
`documented` only attaches OpenAPI metadata. It does not validate incoming values,
change routing, or add a second API registry. Metadata is optional. Without it,
methods, paths, path parameter types, handler names/docstrings, and supported
request/return annotations are inferred. Request query/header/cookie access cannot
be inferred from a function body; document those parameters explicitly. An
unannotated return value has no fabricated response schema. Default error responses
are generic framework descriptions, not a guarantee of application-specific errors.

Pydantic v2 models are detected without making Pydantic a mandatory dependency.
Model definitions are exposed in `components.schemas`. `documented(requestBody=...)`
can describe Request-based JSON bodies and override inferred documentation.

## Frontend and Try it

- Navigation, response status tabs, media types and schemas come from the live
  `/api/openapi.json`. No application endpoints are hardcoded into JavaScript.
- Ctrl+K searches paths, operation IDs, tags, descriptions and schema definitions.
  Arrow keys/Enter select search results; Escape closes dialogs/drawers.
- Shareable hashes encode the method and full path, avoiding operation ID collisions.
- Theme, panel width, group collapse state and desktop sidebar state persist locally.
- Schemas show constraints, nested properties, refs, arrays and oneOf/anyOf/allOf.
  Recursive definitions have expansion limits. Remote refs are displayed but not fetched.
- Send Request performs a real fetch. Status, duration, byte size, headers and raw/body
  results come from that response. Requests time out after 30 seconds and are canceled
  when navigating away. There is no simulated success state.
- curl/Python/JavaScript examples use the current request method, path/query values,
  headers, selected server and body. Required fields and JSON syntax are checked first.
- HTTP errors remain inspectable responses. Network/CORS failures show an explicit error.
- Titles, descriptions, schema values and responses use DOM text nodes, never HTML
  injection or eval. Local assets use the framework's existing safe path resolver.

## Current boundaries

The request editor supports scalar path/query/header inputs and a text body editor
(JSON or other declared media types). Advanced OpenAPI serialization (deepObject,
style/explode for structured arrays/objects), multipart uploads, binary previews,
authorization scheme editors and external `$ref` loading are not implemented.
Cookie parameters are documented, but JavaScript cannot set the Cookie header:
normal browser cookie rules apply. Cross-origin servers must enable their own CORS.
Do not use this UI as an authentication or access control boundary.

OpenAPI generated here remains 3.0.3. Pydantic emits some JSON Schema keywords whose
semantics vary between OpenAPI versions; the explorer displays them but does not
implement a complete OpenAPI/JSON Schema validator. It does not infer runtime
response shapes from Request/Response or dict contents. Metadata can describe those.

A browser check was blocked by this environment's preview isolation (the preview
process could not access the Python runtime). The HTTP routes and actual handler
calls were tested through WSGI; native Windows/Linux WebView visual QA remains to do.

## Development and tests

```
python -m pytest -q
node --test tests/vela_docs_frontend.mjs
```

Python covers registry-derived specs, metadata, Pydantic refs, actual WSGI handler
calls, prefixes, safe assets, docs-disabled behavior and offline HTML. Node covers
indexing, inherited parameters, circular refs, examples, request assembly and snippets.
Existing runtime tests cover compatibility; no change is made to window initialization.
