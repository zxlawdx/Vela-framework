# SPDX-License-Identifier: MPL-2.0
"""Microbenchmarks reproduzíveis do core do Vela.

Execute da raiz do repositório:
    python benchmarks/bench_core.py

Os números são diagnósticos, não gates de CI.
"""

from __future__ import annotations

import io
import json
import logging
import statistics
import tempfile
import time
from pathlib import Path
from wsgiref.util import setup_testing_defaults

from vela.apps import AppRegistry
from vela.core.api_router import ApiRouter
from vela.core.api_server import ApiServer
from vela.core.router import Router
from vela.static import StaticResolver
from vela.template_engine import (
    clear_template_cache,
    compile_template,
    render_string,
    render_template,
)


def samples(callback, *, repeat=200, warmup=20):
    for _ in range(warmup):
        callback()
    values = []
    for _ in range(repeat):
        start = time.perf_counter_ns()
        callback()
        values.append((time.perf_counter_ns() - start) / 1_000_000)
    ordered = sorted(values)
    return {
        "mean_ms": statistics.fmean(values),
        "median_ms": statistics.median(values),
        "p95_ms": ordered[max(0, int(len(ordered) * 0.95) - 1)],
        "p99_ms": ordered[max(0, int(len(ordered) * 0.99) - 1)],
    }


def wsgi_request(app, path):
    env = {}
    setup_testing_defaults(env)
    env.update(
        REQUEST_METHOD="GET",
        PATH_INFO=path,
        CONTENT_LENGTH="0",
        **{"wsgi.input": io.BytesIO(b"")},
    )
    status = []

    def start_response(line, headers, exc_info=None):
        status.append(line)

    body = b"".join(app(env, start_response))
    if not status or not status[0].startswith("200"):
        raise RuntimeError(status or body)
    return body


def benchmark_router_lookup():
    router = Router()
    for index in range(1000):
        router.add(f"/route-{index}", lambda context, index=index: str(index))
    return samples(lambda: router.resolve("/route-999"), repeat=1000)


def benchmark_api_registration(count):
    def run():
        router = ApiRouter()
        for index in range(count):
            router.get(f"/route-{index}")(lambda index=index: index)

    return samples(run, repeat=25, warmup=3)


def benchmark_app_manifest_registration():
    def run():
        registry = AppRegistry()
        for index in range(1000):
            registry.register(f"apps.fixture_{index}")

    return samples(run, repeat=25, warmup=3)


def benchmark_static_url():
    resolver = StaticResolver.for_project(".")
    return samples(lambda: resolver.url("documents/fonts/editor font.woff2"), repeat=1000)


def benchmark_template_parse():
    source = (
        "<main><h1>{{ title }}</h1>"
        + '{{ for("items") }}<p>{{ item.name }}</p>{{ endfor }}' * 10
        + "</main>"
    )
    return samples(lambda: compile_template(source), repeat=500)


def benchmark_template_render():
    source = '<h1>{{ title }}</h1>{{ for("items") }}<p>{{ item.name }}</p>{{ endfor }}'
    compiled = compile_template(source)
    context = {
        "title": "Vela",
        "items": [{"name": f"item-{i}"} for i in range(100)],
    }
    return samples(lambda: compiled.render(context), repeat=300)


def benchmark_template_loop():
    context = {"items": [{"name": f"item-{i}"} for i in range(1000)]}
    return samples(
        lambda: render_string('{{ for("items") }}{{ item.name }}{{ endfor }}', context),
        repeat=100,
        warmup=5,
    )


def benchmark_template_cache():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        template = root / "page.html"
        template.write_text("<p>{{ value }}</p>", encoding="utf-8")
        clear_template_cache()
        miss = samples(
            lambda: (
                clear_template_cache(),
                render_template(str(template), {"value": "x"}, template_roots=[root]),
            ),
            repeat=50,
            warmup=2,
        )
        clear_template_cache()
        render_template(str(template), {"value": "x"}, template_roots=[root])
        hit = samples(
            lambda: render_template(str(template), {"value": "x"}, template_roots=[root]),
            repeat=500,
        )
        return {"miss": miss, "hit": hit}


def benchmark_wsgi_dispatch():
    router = ApiRouter()
    router.get("/ping")(lambda: {"ok": True})
    server = ApiServer(router, port=0)
    server.register_routes()
    return samples(lambda: wsgi_request(server.app, "/api/ping"), repeat=500)


def main():
    logging.disable(logging.CRITICAL)
    result = {
        "router_lookup_1000": benchmark_router_lookup(),
        "api_registration_10": benchmark_api_registration(10),
        "api_registration_100": benchmark_api_registration(100),
        "api_registration_1000": benchmark_api_registration(1000),
        "app_manifest_registration_1000": benchmark_app_manifest_registration(),
        "static_url": benchmark_static_url(),
        "template_parse": benchmark_template_parse(),
        "template_render_100_items": benchmark_template_render(),
        "template_loop_1000": benchmark_template_loop(),
        "template_cache": benchmark_template_cache(),
        "http_wsgi_dispatch": benchmark_wsgi_dispatch(),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
