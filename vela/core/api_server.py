# SPDX-License-Identifier: MPL-2.0
"""Adapter HTTP Bottle/Waitress do Vela with deterministic shutdown."""

from __future__ import annotations

import inspect
import ipaddress
import json
import socket
import time
import warnings
from html import escape
from pathlib import Path
from threading import Thread
from uuid import uuid4
from wsgiref.simple_server import make_server

from bottle import BaseRequest, Bottle, request, response, static_file

from vela.core.api_docs import DOCS_HTML, build_openapi
from vela.core.http import Request, Response, ResponseEncoder
from vela.exceptions import ApiValidationError, ConfigurationError
from vela.log.logger import VelaLogger
from vela.static import StaticResolver

CORE_DIR = Path(__file__).resolve().parent


class ApiServer:
    def __init__(
        self,
        api_router,
        host="127.0.0.1",
        port=8000,
        prefix="/api",
        debug=False,
        static_root="staticfiles",
        auto_port=True,
        server="waitress",
        docs_enabled=True,
        workers=4,
        allow_remote=False,
        cors_origins=(),
        max_body_size=1_048_576,
    ):
        self.api_router = api_router
        self.server = server
        self.docs_enabled = bool(docs_enabled)
        self.workers = max(1, int(workers))
        self.started_at = time.monotonic()
        self.host = str(host)
        self.requested_port = int(port)
        self.auto_port = bool(auto_port) or self.requested_port == 0
        self.port = self.requested_port
        self.prefix = "/" + str(prefix).strip("/")
        self.debug = bool(debug)
        self.static_root = str(static_root)
        self.allow_remote = bool(allow_remote)
        self.cors_origins = tuple(cors_origins or ())
        self.max_body_size = int(max_body_size)
        self.logger = VelaLogger("http")
        self.app = Bottle()
        self._thread: Thread | None = None
        self._waitress_server = None
        self._bottle_server = None
        self._routes_registered = False

        if not self._is_loopback(self.host) and not self.allow_remote:
            raise ConfigurationError(
                f"API em {self.host!r} expõe o processo fora do loopback. "
                "Defina API['allow_remote'] = True explicitamente para permitir."
            )
        if self.max_body_size <= 0:
            raise ConfigurationError("max_body_size deve ser maior que zero.")
        for route in self.api_router.routes:
            if route.path == self.prefix or route.path.startswith(self.prefix + "/"):
                raise ConfigurationError(
                    f"Rota {route.path!r} já contém o prefixo {self.prefix!r}. "
                    f"Declare {route.path[len(self.prefix):] or '/'} no decorator."
                )
        # Bottle's MEMFILE_MAX is an implementation detail. Consumers such as
        # document editors must never need to import/patch Bottle themselves.
        BaseRequest.MEMFILE_MAX = max(int(BaseRequest.MEMFILE_MAX), self.max_body_size + 1)
        self._register_internal_routes()
        if self.debug or self.cors_origins:
            self._enable_cors()

    @staticmethod
    def _is_loopback(host: str) -> bool:
        if host.lower() == "localhost": return True
        try: return ipaddress.ip_address(host).is_loopback
        except ValueError: return False

    @staticmethod
    def _socket_family(host: str):
        return socket.AF_INET6 if ":" in host else socket.AF_INET

    @classmethod
    def is_port_available(cls, host: str, port: int) -> bool:
        try: port = int(port)
        except (TypeError, ValueError): return False
        if port <= 0 or port > 65535: return False
        try:
            with socket.socket(cls._socket_family(host), socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
            return True
        except OSError:
            return False

    @classmethod
    def resolve_port(cls, host: str, preferred_port: int, auto_port: bool = True) -> int:
        preferred_port = int(preferred_port)
        if preferred_port == 0: auto_port = True
        elif cls.is_port_available(host, preferred_port): return preferred_port
        elif not auto_port: raise RuntimeError(f"A porta {preferred_port} já está em uso em {host}.")
        with socket.socket(cls._socket_family(host), socket.SOCK_STREAM) as sock:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])

    def _register_internal_routes(self):
        @self.app.get(self.prefix + "/health")
        def health():
            response.content_type = "application/json; charset=utf-8"
            return json.dumps({"ok": True, "uptime_seconds": round(time.monotonic() - self.started_at, 2)})

        @self.app.get(self.prefix + "/openapi.json")
        def openapi():
            response.content_type = "application/json; charset=utf-8"
            return json.dumps(build_openapi(self.api_router.routes, prefix=self.prefix), ensure_ascii=False)

        if self.docs_enabled:
            @self.app.get(self.prefix + "/docs")
            def docs():
                response.content_type = "text/html; charset=utf-8"
                return DOCS_HTML.replace("__VELA_OPENAPI_PATH__", self.prefix + "/openapi.json")

        @self.app.get("/__vela__/shell")
        def serve_shell():
            content = (CORE_DIR / "shell.html").read_text(encoding="utf-8")
            css = Path.cwd() / self.static_root / "css" / "vela.bundle.css"
            if css.is_file() and "vela.bundle.css" not in content:
                content = content.replace(
                    "</head>",
                    '<link rel="stylesheet" href="/__vela__/static/css/vela.bundle.css" />\n</head>',
                )
            response.content_type = "text/html; charset=utf-8"
            return content

        @self.app.get("/__vela__/static/<filepath:path>")
        def serve_static(filepath):
            return self._serve_static(filepath)

        # Compatibility alias. New application code should always use static().
        @self.app.get("/static/<filepath:path>")
        def serve_static_legacy(filepath):
            return self._serve_static(filepath)

    def _serve_static(self, filepath):
        root = (Path.cwd() / self.static_root).resolve()
        try: target = self._safe_static_target(root, filepath)
        except ValueError:
            response.status = 404
            return "Not found"
        return static_file(str(target.relative_to(root)), root=str(root))

    @staticmethod
    def _safe_static_target(root: Path, filepath: str) -> Path:
        resolver = StaticResolver.for_project(root, collected_root=root)
        try:
            return resolver.resolve_collected(filepath, must_exist=False)
        except (ValueError, FileNotFoundError) as exc:
            raise ValueError("Static path inválido.") from exc

    def _enable_cors(self):
        allowed = set(self.cors_origins)
        if self.debug and self._is_loopback(self.host) and not allowed: allowed.add("*")
        if "*" in allowed and not self._is_loopback(self.host):
            raise ConfigurationError("CORS '*' não é permitido em bind remoto.")

        @self.app.hook("after_request")
        def add_cors_headers():
            origin = request.headers.get("Origin")
            if "*" in allowed: response.headers["Access-Control-Allow-Origin"] = "*"
            elif origin and origin in allowed:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Origin, Accept, Content-Type, X-Requested-With"

        @self.app.route("/<path:path>", method="OPTIONS")
        def options_handler(path): return ""

    def register_routes(self):
        if self._routes_registered: return
        for route in self.api_router.routes:
            self.app.route(
                self.prefix + route.path,
                method=route.method,
                callback=self._wrap_handler(route),
            )
        if self.debug: self._register_debug_routes()
        self._routes_registered = True

    def _wrap_handler(self, route):
        binder = self._compile_binder(route)
        def wrapper(**path_params):
            t0 = time.perf_counter()
            try:
                body, data = self._read_request_body()
                request_model = Request(
                    method=request.method,
                    path=request.path,
                    query=dict(request.query),
                    headers=dict(request.headers),
                    json=data,
                    body=body,
                    path_params={str(key): str(value) for key, value in path_params.items()},
                )
                result = route.handler(*binder(request_model, data))
                return self._encode_response(result)
            except ApiValidationError as exc:
                return self._error_response(422, "validation_error", str(exc))
            except ValueError as exc:
                return self._error_response(400, "invalid_request", str(exc))
            except Exception as exc:
                error_id = "VELA-E-" + uuid4().hex[:8]
                self.logger.exception(f"{error_id} exception em {request.method} {request.path}: {exc}")
                message = str(exc) if self.debug else f"Erro interno. Código: {error_id}"
                return self._error_response(500, "internal_error", message, error_id=error_id)
            finally:
                if self.debug:
                    elapsed = (time.perf_counter() - t0) * 1000
                    self.logger.debug(f"{request.method} {request.path}: {elapsed:.1f} ms")
        return wrapper

    def _compile_binder(self, route):
        params = tuple(route.signature.parameters.values())
        if not params: return lambda req, data: ()
        if len(params) != 1:
            raise ConfigurationError(f"Handler {getattr(route.handler, '__name__', route.handler)!r} deve receber 0 ou 1 parâmetro.")
        param = params[0]
        annotation = route.type_hints.get(param.name, param.annotation)
        if annotation is Request: return lambda req, data: (req,)
        if hasattr(annotation, "model_validate"):
            def bind_model(req, data):
                try: return (annotation.model_validate(data),)
                except Exception as exc: raise ApiValidationError(str(exc)) from exc
            return bind_model
        if param.name == "context":
            if self.debug: warnings.warn("Handlers `context` são legados; prefira `request: Request`.", DeprecationWarning, stacklevel=3)
            return lambda req, data: ({"query": dict(req.query), "headers": dict(req.headers), "body": data, "json": data, "method": req.method, "path": req.path, "path_params": dict(req.path_params)},)
        if param.name == "data":
            if self.debug: warnings.warn("Handlers `data` são legados; prefira `request: Request`.", DeprecationWarning, stacklevel=3)
            return lambda req, data: (data,)
        if annotation in (dict, inspect.Signature.empty): return lambda req, data: (data,)
        raise ConfigurationError(f"Não foi possível vincular o parâmetro {param.name!r}; use Request ou modelo Pydantic.")

    def _read_request_body(self) -> tuple[bytes, object]:
        length = request.content_length
        if length is not None and length > self.max_body_size:
            response.status = 413
            raise ApiValidationError(f"Request body excede o limite de {self.max_body_size} bytes.")
        if request.method in {"GET", "HEAD", "OPTIONS"}: return b"", {}
        raw = request.body.read(self.max_body_size + 1)
        if len(raw) > self.max_body_size:
            response.status = 413
            raise ApiValidationError(f"Request body excede o limite de {self.max_body_size} bytes.")
        if not raw: return raw, {}
        if "json" not in (request.content_type or "").lower(): return raw, {}
        try: return raw, json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise ValueError("JSON inválido.") from exc

    def _encode_response(self, result):
        explicit = result if isinstance(result, Response) else None
        body = explicit.body if explicit else result
        if explicit:
            response.status = explicit.status
            for key, value in explicit.headers.items(): response.headers[str(key)] = str(value)
            if explicit.content_type: response.content_type = explicit.content_type
        if isinstance(body, bytes):
            if not explicit or not explicit.content_type: response.content_type = "application/octet-stream"
            return body
        if isinstance(body, str):
            if not explicit or not explicit.content_type: response.content_type = "text/html; charset=utf-8"
            return body
        response.content_type = explicit.content_type if explicit and explicit.content_type else "application/json; charset=utf-8"
        return ResponseEncoder.json_dumps(body)

    def _error_response(self, status, code, message, *, error_id=None):
        if response.status_code == 413:
            status, code = 413, "payload_too_large"
        response.status = status
        response.content_type = "application/json; charset=utf-8"
        payload = {"ok": False, "error": {"code": code, "message": message}}
        if error_id: payload["error"]["id"] = error_id
        return ResponseEncoder.json_dumps(payload)

    def _register_debug_routes(self):
        @self.app.get("/__vela__/api/routes")
        def debug_routes():
            response.content_type = "text/html; charset=utf-8"
            cards = []
            for route in self.api_router.routes:
                method = escape(route.method, quote=True)
                path = escape(self.prefix + route.path, quote=True)
                handler = escape(getattr(route.handler, "__name__", "handler"), quote=True)
                cards.append(f'<section class="route"><strong>{method}</strong> <code>{path}</code><small>handler: {handler}</small></section>')
            routes_html = "".join(cards) or "<p>Nenhuma rota de API registrada.</p>"
            return "<!doctype html><html><head><meta charset='utf-8'><title>Vela API Debug</title></head><body><h1>Vela API Debug</h1>" + routes_html + "</body></html>"

    def _create_waitress_server(self, port: int):
        from waitress import create_server
        return create_server(self.app, host=self.host, port=port, threads=self.workers)

    @staticmethod
    def _bound_port(server, fallback: int) -> int:
        effective = getattr(server, "effective_port", None)
        if effective: return int(effective)
        getter = getattr(server, "getsockname", None)
        if callable(getter):
            sockname = getter()
            if isinstance(sockname, tuple) and len(sockname) >= 2: return int(sockname[1])
        adj = getattr(server, "adj", None)
        if adj is not None and getattr(adj, "port", None): return int(adj.port)
        return int(fallback)

    def start(self):
        self.register_routes()
        if self.server == "waitress":
            desired = self.requested_port
            try: self._waitress_server = self._create_waitress_server(desired)
            except OSError:
                if not self.auto_port: raise RuntimeError(f"A porta {desired} já está em uso em {self.host}.")
                self._waitress_server = self._create_waitress_server(0)
            self.port = self._bound_port(self._waitress_server, desired)
            self._thread = Thread(target=self._waitress_server.run, daemon=True, name="vela-http")
            self._thread.start()
            return self.port
        if self.server == "bottle":
            desired = self.requested_port
            try:
                self._bottle_server = make_server(self.host, desired, self.app)
            except OSError:
                if not self.auto_port: raise RuntimeError(f"A porta {desired} já está em uso em {self.host}.")
                self._bottle_server = make_server(self.host, 0, self.app)
            self.port = int(self._bottle_server.server_port)
            self._thread = Thread(target=self._bottle_server.serve_forever, daemon=True, name="vela-http")
            self._thread.start()
            return self.port
        raise ValueError(f"Servidor desconhecido: {self.server}")

    def wait_until_ready(self, timeout: float = 10.0):
        deadline = time.monotonic() + timeout
        probe_host = "127.0.0.1" if self.host == "0.0.0.0" else "::1" if self.host == "::" else self.host
        while time.monotonic() < deadline:
            try:
                with socket.create_connection((probe_host, self.port), timeout=0.5): return True
            except OSError: time.sleep(0.05)
        raise RuntimeError(f"Servidor Vela não respondeu em {self.host}:{self.port} após {timeout}s.")

    def stop(self):
        waitress_server, self._waitress_server = self._waitress_server, None
        bottle_server, self._bottle_server = self._bottle_server, None
        if waitress_server is not None:
            try: waitress_server.close()
            except Exception as exc: self.logger.warning(f"Falha ao fechar Waitress: {exc}")
        if bottle_server is not None:
            try:
                bottle_server.shutdown()
                bottle_server.server_close()
            except Exception as exc: self.logger.warning(f"Falha ao fechar servidor Bottle: {exc}")
        thread, self._thread = self._thread, None
        if thread is not None and thread.is_alive(): thread.join(timeout=2.0)
