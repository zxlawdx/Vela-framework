from bottle import Bottle, request, response, run
from threading import Thread
import inspect
import json


class ApiServer:
    def __init__(
        self,
        api_router,
        host="127.0.0.1",
        port=8000,
        prefix="/api",
        debug=False,
    ):
        self.api_router = api_router
        self.host = host
        self.port = port
        self.prefix = prefix
        self.debug = debug
        self.app = Bottle()
        if debug == True:
            self._enable_cors()

    def _enable_cors(self):
        @self.app.hook("after_request")
        def add_cors_headers():
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Origin, Accept, Content-Type, X-Requested-With"

        @self.app.route("/<path:path>", method="OPTIONS")
        def options_handler(path):
            return ""

    def register_routes(self):
        for route in self.api_router.routes:
            method = route["method"]
            path = self.prefix + route["path"]
            handler = route["handler"]

            print(f"[VELA API] Registrando rota: {method} {path}")

            self.app.route(
                path,
                method=method,
                callback=self._wrap_handler(handler),
            )

        if self.debug:
            self._register_debug_routes()

    def _wrap_handler(self, handler):
        def wrapper():
            data = request.json or {}

            context = {
                "query": dict(request.query),
                "headers": dict(request.headers),
                "body": data,
                "json": data,
                "method": request.method,
                "path": request.path,
            }

            params = inspect.signature(handler).parameters

            if "context" in params:
                result = handler(context)

            elif "data" in params:
                result = handler(data)

            else:
                result = handler()

            # Se o handler já retornou uma resposta pronta do Bottle
            if hasattr(result, "status_code"):
                return result

            # JSON automático só para dict/list
            if isinstance(result, (dict, list)):
                response.content_type = "application/json; charset=utf-8"
                return json.dumps(result, ensure_ascii=False)

            # String vira HTML/texto puro
            if isinstance(result, str):
                response.content_type = "text/html; charset=utf-8"
                return result

            # Fallback
            response.content_type = "application/json; charset=utf-8"
            return json.dumps(result, ensure_ascii=False)

        return wrapper

    def _register_debug_routes(self):
        @self.app.get("/__vela__/api/routes")
        def debug_routes():
            response.content_type = "text/html; charset=utf-8"

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

        thread = Thread(
            target=lambda: run(
                app=self.app,
                host=self.host,
                port=self.port,
                quiet=True,
            ),
            daemon=True,
        )

        thread.start()