# SPDX-License-Identifier: MPL-2.0
"""Microbenchmark de despacho local. Nao inclui GUI, rede, DB nem Waitress.

python benchmarks/bench_local_api.py --requests 10000
"""
import argparse
import io
import json
from statistics import mean
from time import perf_counter
from wsgiref.util import setup_testing_defaults

from vela.core.api_router import ApiRouter
from vela.core.api_server import ApiServer


def ping():
    return {"ok": True}


def echo(data):
    return {"received": data}


def request(app, path, method="GET", body=b""):
    environ = {}
    setup_testing_defaults(environ)
    environ["PATH_INFO"] = path
    environ["REQUEST_METHOD"] = method
    environ["CONTENT_TYPE"] = "application/json"
    environ["CONTENT_LENGTH"] = str(len(body))
    environ["wsgi.input"] = io.BytesIO(body)
    status = []
    def start(code, headers, exc_info=None):
        status.append(code)
    output = b"".join(app(environ, start))
    if not status[0].startswith("200"):
        raise AssertionError((status[0], output))
    return output


def bench(app, path, method, body, times):
    for _ in range(100):  # aquecimento
        request(app, path, method, body)
    samples = []
    for _ in range(times):
        start = perf_counter()
        request(app, path, method, body)
        samples.append((perf_counter() - start) * 1000)
    samples.sort()
    return {"mean_ms": round(mean(samples), 4),
            "median_ms": round(samples[len(samples) // 2], 4),
            "p95_ms": round(samples[int(len(samples) * .95)], 4)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=5000)
    args = parser.parse_args()
    if args.requests < 100:
        parser.error("--requests deve ser >= 100")
    routes = ApiRouter()
    routes.get("/ping")(ping)
    routes.post("/echo")(echo)
    server = ApiServer(routes, port=0, debug=False, server="waitress")
    server.register_routes()
    print("Microbenchmark WSGI Bottle interno: sem servidor HTTP/Waitress, GUI ou DB")
    for name, path, method, body in [
        ("GET zero args", "/api/ping", "GET", b""),
        ("POST JSON", "/api/echo", "POST", json.dumps({"key": "value"}).encode()),
    ]:
        print(name, bench(server.app, path, method, body, args.requests))
    print("Nao compare estes valores diretamente com Django sem teste equivalente.")


if __name__ == "__main__":
    main()
