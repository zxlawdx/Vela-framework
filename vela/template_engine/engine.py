import os
import re


def _resolve_url(name: str, router) -> str:
    if router is None:
        return f"/#url-not-resolved-{name}"
    try:
        return router.url_for(name)
    except KeyError:
        return f"/#route-{name}-not-found"


def _resolve_static(path: str, static_root: str = "staticfiles") -> str:
    base = os.path.join(os.getcwd(), static_root)
    full = os.path.join(base, path)
    return "file:///" + full.replace("\\", "/").lstrip("/")


def _resolve_variable(expr: str, context: dict):
    current = context

    for part in expr.split("."):
        if isinstance(current, dict):
            current = current.get(part, "")
        else:
            current = getattr(current, part, "")

    return current


def _evaluate_expression(expr: str, context: dict, router, static_root: str) -> str:
    expr = expr.strip()

    url_match = re.match(r"""^url\(\s*['"](.+?)['"]\s*\)$""", expr)
    if url_match:
        return _resolve_url(url_match.group(1), router)

    static_match = re.match(r"""^static\(\s*['"](.+?)['"]\s*\)$""", expr)
    if static_match:
        return _resolve_static(static_match.group(1), static_root)

    # variável simples ou com ponto: title, item.name, item.path
    if re.match(r"^\w+(\.\w+)*$", expr):
        return str(_resolve_variable(expr, context))

    return f"<!-- vela: expressão não suportada: {expr} -->"


def _process_for_blocks(source: str, context: dict, router, static_root: str) -> str:
    pattern = re.compile(
        r"""\{\{\s*for\(\s*['"](.+?)['"]\s*\)\s*\}\}(.*?)\{\{\s*endfor\s*\}\}""",
        re.DOTALL,
    )

    def replace_for(match):
        collection_name = match.group(1)
        block = match.group(2)

        items = _resolve_variable(collection_name, context)

        if not items:
            return ""

        result = ""

        for item in items:
            local_context = context.copy()
            local_context["item"] = item

            result += render_string(
                block,
                context=local_context,
                router=router,
                static_root=static_root,
            )

        return result

    return pattern.sub(replace_for, source)


def render_string(
    source: str,
    context: dict = None,
    router=None,
    static_root: str = "staticfiles",
) -> str:
    context = context or {}

    # primeiro processa blocos for
    source = _process_for_blocks(source, context, router, static_root)

    def replace_expr(match):
        expr = match.group(1)
        return _evaluate_expression(expr, context, router, static_root)

    return re.sub(r"\{\{\s*(.+?)\s*\}\}", replace_expr, source)


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

    with open(full_path, encoding="utf-8") as f:
        source = f.read()

    return render_string(
        source,
        context=context,
        router=router,
        static_root=static_root,
    )