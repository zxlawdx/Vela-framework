# SPDX-License-Identifier: MPL-2.0
import os
import re
from functools import lru_cache
from pathlib import Path


# ─── Funções de resolução ─────────────────────────────────────────────────────

def _resolve_url(name: str, router) -> str:
    if router is None:
        return f"/#url-not-resolved-{name}"

    try:
        return router.url_for(name)
    except KeyError:
        return f"/#route-{name}-not-found"


def _resolve_static(path: str, static_root: str = "staticfiles", base_url: str = None) -> str:
    if base_url:
        return f"{base_url}/__vela__/static/{path}"
    base = os.path.join(os.getcwd(), static_root)
    full = os.path.join(base, path)
    url = "file:///" + full.replace("\\", "/").lstrip("/")
    return url


# ─── Parser de expressões ─────────────────────────────────────────────────────

def _evaluate_expression(expr: str, context: dict, router, static_root: str) -> str:
    expr = expr.strip()

    url_match = re.match(r"""^url\(\s*['"](.+?)['"]\s*\)$""", expr)
    if url_match:
        name = url_match.group(1)
        return _resolve_url(name, router)

    static_match = re.match(r"""^static\(\s*['"](.+?)['"]\s*\)$""", expr)
    if static_match:
        path = static_match.group(1)
        return _resolve_static(path, static_root, base_url=context.get("__base_url__"))

    if re.match(r"^\w+$", expr):
        value = context.get(expr, "")
        return str(value)

    return f"<!-- vela: expressão não suportada: {expr} -->"


# ─── Estruturas de template ───────────────────────────────────────────────────

def _render_inline_variables(source: str, context: dict, router, static_root: str) -> str:
    def replace_expr(match):
        expr = match.group(1)
        return _evaluate_expression(expr, context, router, static_root)

    return re.sub(r"\{\{\s*(.+?)\s*\}\}", replace_expr, source)


import re


def for_expressions(expr, context, router, static_root):

    pattern = re.compile(
        r'\{\{\s*for\("([^"]+)"\)\s*\}\}(.*?)\{\{\s*endfor\s*\}\}',
        re.DOTALL
    )

    matches = pattern.finditer(expr)

    result = expr

    for match in matches:

        full_match = match.group(0)

        key = match.group(1)

        block = match.group(2)

        items = context.get(key, [])

        rendered_items = ""

        for item in items:

            rendered = block

            if isinstance(item, dict):

                for k, v in item.items():

                    rendered = rendered.replace(
                        f"{{{{ item.{k} }}}}",
                        str(v)
                    )

            rendered_items += rendered

        result = result.replace(full_match, rendered_items)

    return result

# ─── Renderizador principal ───────────────────────────────────────────────────
def render_string(
    source: str,
    context: dict = None,
    router=None,
    static_root: str = "staticfiles",
) -> str:
    context = context or {}

    # Injeta base_url do router no context para que static() gere URLs http://
    if router and getattr(router, "base_url", None) and "__base_url__" not in context:
        context["__base_url__"] = router.base_url

    source = for_expressions(
        source,
        context,
        router,
        static_root
    )

    processed = _render_inline_variables(
        source,
        context,
        router,
        static_root
    )

    return processed

@lru_cache(maxsize=256)
def _read_template_cached(path, mtime_ns, size):
    # Chave inclui estatisticas para invalidar automaticamente em dev.
    return Path(path).read_text(encoding="utf-8")


def render_template(
    template_path: str,
    context: dict = None,
    router=None,
    static_root: str = "staticfiles",
) -> str:
    context = context or {}

    full_path = os.path.join(os.getcwd(), template_path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Template não encontrado: {full_path}")

    metadata = os.stat(full_path)
    source = _read_template_cached(full_path, metadata.st_mtime_ns, metadata.st_size)

    return render_string(
        source,
        context=context,
        router=router,
        static_root=static_root
    )