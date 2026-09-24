# SPDX-License-Identifier: MPL-2.0
from bottle import Bottle, request, response, run, static_file
from threading import Thread
from pathlib import Path
from vela.core.api_docs import build_openapi, DOCS_HTML
import inspect
import json
import socket
import time

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
        server='waitress',
        docs_enabled=True,
        workers=4,
    ):
        self.api_router = api_router
        self.server = server
        self.docs_enabled = docs_enabled
        self.workers = max(1, int(workers))
        self.started_at = time.monotonic()
        self.host = host

        # Guarda a porta solicitada e resolve a porta efetiva antes
        # de subir o Bottle. Se a porta estiver ocupada, o SO escolhe
        # uma porta livre quando auto_port=True.
        self.requested_port = int(port)
        self.auto_port = auto_port
        self.port = self.resolve_port(
            host=self.host,
            preferred_port=self.requested_port,
            auto_port=self.auto_port,
        )

        self.prefix = prefix
        self.debug = debug
        self.static_root = static_root
        self.app = Bottle()

        self._register_internal_routes()

        if debug == True:
            self._enable_cors()

    @staticmethod
    def _socket_family(host: str):
        """
        Retorna a família de socket apropriada para o host configurado.
        O Vela usa IPv4 por padrão, mas mantém suporte básico a IPv6.
        """
        return socket.AF_INET6 if ":" in host else socket.AF_INET

    @classmethod
    def is_port_available(cls, host: str, port: int) -> bool:
        """
        Verifica se uma porta TCP pode ser usada pelo servidor local.

        O teste é feito por bind, sem iniciar listener. Isso detecta
        corretamente quando outra instância do Vela ou outro processo
        já está usando a porta.
        """
        try:
            port = int(port)
        except (TypeError, ValueError):
            return False

        if port <= 0 or port > 65535:
            return False

        family = cls._socket_family(host)

        try:
            with socket.socket(family, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
            return True
        except OSError:
            return False

    @classmethod
    def resolve_port(
        cls,
        host: str,
        preferred_port: int,
        auto_port: bool = True,
    ) -> int:
        """
        Resolve a porta que o servidor deve usar.

        Fluxo:
          1. Tenta manter a porta configurada.
          2. Se estiver ocupada e auto_port=False, interrompe com erro claro.
          3. Se estiver ocupada e auto_port=True, pede ao SO uma porta livre.

        Usar bind(host, 0) delega ao sistema operacional a escolha de uma
        porta efêmera disponível, evitando uma busca manual 8001, 8002, ...
        """
        try:
            preferred_port = int(preferred_port)
        except (TypeError, ValueError):
            raise ValueError("A porta da API deve ser um número inteiro.")

        if preferred_port == 0:
            auto_port = True
        elif cls.is_port_available(host, preferred_port):
            return preferred_port
        elif not auto_port:
            raise RuntimeError(
                f"A porta {preferred_port} já está em uso em {host}. "
                "Defina API['auto_port'] = True para permitir fallback automático."
            )

        family = cls._socket_family(host)

        try:
            with socket.socket(family, socket.SOCK_STREAM) as sock:
                sock.bind((host, 0))
                return int(sock.getsockname()[1])
        except OSError as exc:
            raise RuntimeError(
                f"Não foi possível encontrar uma porta livre para o Vela em {host}."
            ) from exc

    def _register_internal_routes(self):
        @self.app.get(self.prefix + "/health")
        def health():
            response.content_type = "application/json"
            return json.dumps({"ok": True, "uptime_seconds": round(time.monotonic() - self.started_at, 2)})

        @self.app.get(self.prefix + "/openapi.json")
        def openapi():
            response.content_type = "application/json"
            return json.dumps(build_openapi(self.api_router.routes, prefix=self.prefix),
                              ensure_ascii=False)

        if self.docs_enabled:
            @self.app.get(self.prefix + "/docs")
            def docs():
                response.content_type = "text/html; charset=utf-8"
                return DOCS_HTML.replace("__VELA_OPENAPI_PATH__",
                                         self.prefix + "/openapi.json")

        @self.app.get("/__vela__/shell")
        def serve_shell():
            # Em builds offline, usa CSS ja compilado no lugar da CDN.
            css = Path.cwd() / self.static_root / "css" / "vela.bundle.css"
            if css.is_file():
                import re
                content = (CORE_DIR / "shell.html").read_text(encoding="utf-8")
                content = content.replace(
                    '<script src="https://cdn.tailwindcss.com"></script>',
                    '<link rel="stylesheet" href="/__vela__/static/css/vela.bundle.css">')
                content = re.sub(
                    r"<script>\s*tailwind\.config\s*=.*?</script>", "",
                    content, flags=re.DOTALL, count=1)
                content = re.sub(
                    r"^\s*<link[^>]+(?:fonts\.googleapis|fonts\.gstatic)[^>]*>\s*$",
                    "", content, flags=re.MULTILINE)
                response.content_type = "text/html; charset=utf-8"
                return content
            return static_file("shell.html", root=str(CORE_DIR))

        @self.app.get("/__vela__/static/<filepath:path>")
        def serve_static(filepath):
            import os
            root = os.path.join(os.getcwd(), self.static_root)
            return static_file(filepath, root=root)

    def wait_until_ready(self, timeout: float = 10.0):
        """
        Bloqueia até que o servidor HTTP esteja aceitando conexões TCP.

        Resolve a race condition onde pywebview tenta carregar /__vela__/shell
        antes do Bottle ter subido completamente na thread daemon.

        Args:
            timeout: Tempo máximo de espera em segundos (default: 10s).

        Raises:
            RuntimeError: Se o servidor não responder dentro do timeout.
        """
        deadline = time.time() + timeout

        # 0.0.0.0/:: são endereços de bind, não destinos ideais para probe.
        probe_host = self.host
        if probe_host == "0.0.0.0":
            probe_host = "127.0.0.1"
        elif probe_host == "::":
            probe_host = "::1"

        while time.time() < deadline:
            try:
                with socket.create_connection((probe_host, self.port), timeout=0.5):
                    return True
            except OSError:
                time.sleep(0.05)
        raise RuntimeError(
            f"Servidor Vela não respondeu em {self.host}:{self.port} "
            f"após {timeout}s. Verifique se a porta não está em uso."
        )

    def _enable_cors(self):
        @self.app.hook("after_request")
        def add_cors_headers():
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, POST, PUT, DELETE, OPTIONS"
            )
            response.headers["Access-Control-Allow-Headers"] = (
                "Origin, Accept, Content-Type, X-Requested-With"
            )

        @self.app.route("/<path:path>", method="OPTIONS")
        def options_handler(path):
            return ""

    def register_routes(self):
        for route in self.api_router.routes:
            method = route["method"]
            path = self.prefix + route["path"]
            handler = route["handler"]

            print(
                f"[VELA API] Registrando rota: "
                f"{method} {path}"
            )

            self.app.route(
                path,
                method=method,
                callback=self._wrap_handler(handler),
            )

        if self.debug:
            self._register_debug_routes()

    def _wrap_handler(self, handler):
        # Metadados do handler sao calculados uma vez por rota.
        params = inspect.signature(handler).parameters
        argument = "context" if "context" in params else "data" if "data" in params else None
        annotation = params[argument].annotation if argument else inspect.Signature.empty

        def wrapper():
            t0 = time.perf_counter()
            if argument in ("data", "context"):
                data = request.json or {}
            if argument == "context":
                context = {
                    "query": dict(request.query),
                    "headers": dict(request.headers),
                    "body": data,
                    "json": data,
                    "method": request.method,
                    "path": request.path,
                }
                result = handler(context)
            elif argument == "data":
                if hasattr(annotation, "model_validate"):
                    result = handler(annotation.model_validate(data))
                else:
                    result = handler(data)
            else:
                result = handler()

            if self.debug:
                elapsed = (time.perf_counter() - t0) * 1000
                print(f"[VELA PERF] {request.method} {request.path}: {elapsed:.1f} ms")

            if hasattr(result, "status_code"):
                return result

            if isinstance(result, (dict, list)):
                response.content_type = (
                    "application/json; charset=utf-8"
                )
                return json.dumps(
                    result,
                    ensure_ascii=False
                )

            if isinstance(result, str):
                response.content_type = (
                    "text/html; charset=utf-8"
                )
                return result

            response.content_type = (
                "application/json; charset=utf-8"
            )

            return json.dumps(
                result,
                ensure_ascii=False
            )

        return wrapper

    def _register_debug_routes(self):
        @self.app.get("/__vela__/api/routes")
        def debug_routes():
            response.content_type = (
                "text/html; charset=utf-8"
            )

            routes_html = ""

            for idx, route in enumerate(self.api_router.routes):
                method = route["method"]
                path = self.prefix + route["path"]
                handler = route["handler"].__name__
                badge_class = method.lower()

                routes_html += f"""
                <div class="route-card">
                    <div class="route-top">
                        <span class="badge badge-{badge_class}">{method}</span>
                        <code class="route-path">{path}</code>

                        <button class="tester-toggle" onclick="toggleTester({idx})">
                            Testar
                        </button>
                    </div>

                    <div class="route-handler">
                        handler: <code>{handler}</code>
                    </div>

                    <div class="tester" id="tester-{idx}">
                        <label>Corpo da requisição JSON</label>

                        <textarea id="body-{idx}" placeholder='{{"nome": "Cliente"}}'></textarea>

                        <div class="tester-actions">
                            <button class="btn-send" onclick="sendRequest('{method}', '{path}', {idx})">
                                Enviar
                            </button>

                            <button class="btn-clear" onclick="clearResult({idx})">
                                Limpar
                            </button>

                            <span class="status-pill" id="status-{idx}" style="display:none;"></span>
                        </div>

                        <pre class="result-block" id="result-{idx}"></pre>
                    </div>
                </div>
                """

            if not routes_html:
                routes_html = """
                <div class="empty">
                    Nenhuma rota de API registrada.
                </div>
                """

            return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Vela API Debug</title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            padding: 32px;
            background: #0f172a;
            color: #e2e8f0;
            font-family: Arial, sans-serif;
        }}

        h1 {{
            margin: 0 0 6px;
            font-size: 28px;
            color: #ffffff;
        }}

        p {{
            margin: 0 0 24px;
            color: #94a3b8;
        }}

        .route-card {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
        }}

        .route-top {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .badge {{
            min-width: 70px;
            text-align: center;
            padding: 5px 10px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: bold;
            border: 1px solid;
        }}

        .badge-get {{
            background: #1e3a5f;
            color: #93c5fd;
            border-color: #2563eb;
        }}

        .badge-post {{
            background: #14532d;
            color: #86efac;
            border-color: #16a34a;
        }}

        .badge-put {{
            background: #451a03;
            color: #fde68a;
            border-color: #ca8a04;
        }}

        .badge-delete {{
            background: #450a0a;
            color: #fca5a5;
            border-color: #dc2626;
        }}

        .route-path {{
            flex: 1;
            color: #e2e8f0;
            font-family: monospace;
            font-size: 14px;
        }}

        .route-handler {{
            margin-top: 8px;
            color: #94a3b8;
            font-size: 13px;
        }}

        .tester-toggle {{
            border: 1px solid #475569;
            background: transparent;
            color: #e2e8f0;
            padding: 6px 10px;
            border-radius: 8px;
            cursor: pointer;
        }}

        .tester-toggle:hover {{
            background: #334155;
        }}

        .tester {{
            display: none;
            margin-top: 14px;
            padding-top: 14px;
            border-top: 1px solid #334155;
        }}

        .tester.open {{
            display: block;
        }}

        label {{
            display: block;
            margin-bottom: 6px;
            color: #94a3b8;
            font-size: 13px;
        }}

        textarea {{
            width: 100%;
            min-height: 100px;
            background: #020617;
            color: #e2e8f0;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 10px;
            font-family: monospace;
            resize: vertical;
        }}

        .tester-actions {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 10px;
        }}

        .btn-send,
        .btn-clear {{
            border: none;
            border-radius: 8px;
            padding: 8px 12px;
            color: white;
            cursor: pointer;
        }}

        .btn-send {{
            background: #2563eb;
        }}

        .btn-clear {{
            background: #475569;
        }}

        .status-pill {{
            padding: 4px 10px;
            border-radius: 999px;
            background: #020617;
            border: 1px solid #334155;
            font-size: 12px;
        }}

        .result-block {{
            display: none;
            margin-top: 10px;
            padding: 12px;
            background: #020617;
            border: 1px solid #334155;
            border-radius: 8px;
            color: #e2e8f0;
            white-space: pre-wrap;
            overflow-x: auto;
        }}

        .empty {{
            padding: 16px;
            border: 1px dashed #475569;
            border-radius: 12px;
            color: #94a3b8;
            background: #1e293b;
        }}
    </style>
</head>

<body>
    <h1>Vela API Debug</h1>
    <p>Rotas registradas na API do Vela</p>

    {routes_html}

    <script>
        function toggleTester(idx) {{
            const tester = document.getElementById("tester-" + idx);
            tester.classList.toggle("open");
        }}

        function clearResult(idx) {{
            const result = document.getElementById("result-" + idx);
            const status = document.getElementById("status-" + idx);

            result.style.display = "none";
            result.textContent = "";

            status.style.display = "none";
            status.textContent = "";
        }}

        async function sendRequest(method, path, idx) {{
            const bodyEl = document.getElementById("body-" + idx);
            const result = document.getElementById("result-" + idx);
            const status = document.getElementById("status-" + idx);

            const options = {{
                method: method,
                headers: {{}}
            }};

            if (method !== "GET" && method !== "DELETE") {{
                options.headers["Content-Type"] = "application/json";
                options.body = bodyEl.value || "{{}}";
            }}

            try {{
                const res = await fetch(path, options);
                const text = await res.text();

                status.style.display = "inline-block";
                status.textContent = res.status;

                result.style.display = "block";
                result.textContent = text;
            }} catch (err) {{
                status.style.display = "inline-block";
                status.textContent = "ERRO";

                result.style.display = "block";
                result.textContent = err.message;
            }}
        }}
    </script>
</body>
</html>"""

    def start(self):
        self.register_routes()

        def serve():
            if self.server == "waitress":
                from waitress import serve as waitress_serve
                waitress_serve(self.app, host=self.host, port=self.port,
                               threads=self.workers)
            elif self.server == "bottle":
                run(app=self.app, host=self.host, port=self.port, quiet=True)
            else:
                raise ValueError(f"Servidor desconhecido: {self.server}")

        thread = Thread(target=serve, daemon=True)

        thread.start()