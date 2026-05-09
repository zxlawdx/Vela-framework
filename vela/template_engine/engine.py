"""
vela.template_engine.engine
============================
Engine de templates do Vela.

Suporta:
  {{ variavel }}              → substitui variável simples do context
  {{ url('nome') }}           → resolve rota nomeada para seu path
  {{ static('app/file.css') }}→ resolve caminho para arquivo estático

Uso:
    from vela.template_engine.engine import render_template, render_string

    # A partir de um arquivo
    html = render_template("apps/dashboard/templates/index.html", {
        "title": "Dashboard",
        "user": "Dev",
    }, router=router)

    # A partir de uma string
    html = render_string("<h1>{{ title }}</h1>", {"title": "Olá"})

Links internos gerados pelo url() são automaticamente marcados
com data-vela-link para interceptação pelo runtime JS:

    {{ url('dashboard') }}   →  /dashboard
    
    Uso em templates:
        <a href="{{ url('dashboard') }}" data-vela-link>Dashboard</a>

O dev pode omitir data-vela-link se usar {{ url() }} dentro de href,
pois o JS detecta automaticamente hrefs que começam com "/".
"""

import os
import re


# ─── Funções de resolução ─────────────────────────────────────────────────────

def _resolve_url(name: str, router) -> str:
    """
    Resolve o path de uma rota nomeada.
    Se o router não estiver disponível, retorna /#.
    """
    if router is None:
        return f"/#url-not-resolved-{name}"
    try:
        return router.url_for(name)
    except KeyError:
        return f"/#route-{name}-not-found"


def _resolve_static(path: str, static_root: str = "staticfiles") -> str:
    """
    Resolve o caminho de um arquivo estático.

    Para pywebview, arquivos locais precisam de caminho absoluto
    com protocolo file:// ou um path relativo que funcione com
    o servidor interno do webview.

    Estratégia:
      - Em dev: file:// + caminho absoluto
      - O dev pode sobrescrever static_root via settings.STATIC_ROOT
    """
    base = os.path.join(os.getcwd(), static_root)
    full = os.path.join(base, path)
    # Converte separadores para URL e adiciona file://
    url = "file:///" + full.replace("\\", "/").lstrip("/")
    return url


# ─── Parser de expressões ─────────────────────────────────────────────────────

def _evaluate_expression(expr: str, context: dict, router, static_root: str) -> str:
    """
    Avalia uma expressão dentro de {{ ... }}.

    Exemplos de expressões suportadas:
        variavel
        url('nome')
        static('app/file.css')
    """
    expr = expr.strip()

    # {{ url('nome') }} ou {{ url("nome") }}
    url_match = re.match(r"""^url\(\s*['"](.+?)['"]\s*\)$""", expr)
    if url_match:
        name = url_match.group(1)
        return _resolve_url(name, router)

    # {{ static('path/to/file') }} ou {{ static("path/to/file") }}
    static_match = re.match(r"""^static\(\s*['"](.+?)['"]\s*\)$""", expr)
    if static_match:
        path = static_match.group(1)
        return _resolve_static(path, static_root)

    # {{ variavel_simples }}
    if re.match(r"^\w+$", expr):
        value = context.get(expr, "")
        return str(value)

    # Expressão não reconhecida — retorna vazia com aviso no template
    return f"<!-- vela: expressão não suportada: {expr} -->"


# ─── Renderizador principal ───────────────────────────────────────────────────

def render_string(
    source: str,
    context: dict = None,
    router=None,
    static_root: str = "staticfiles",
) -> str:
    """
    Renderiza uma string de template e retorna HTML processado.

    Args:
        source      String HTML com expressões {{ ... }}
        context     Dicionário de variáveis
        router      Instância de Router (para url())
        static_root Caminho base para arquivos estáticos

    Returns:
        String HTML com expressões substituídas.
    """
    context = context or {}

    def replace_expr(match):
        expr = match.group(1)
        return _evaluate_expression(expr, context, router, static_root)

    # Substitui todas as ocorrências de {{ ... }}
    # Regex: chaves duplas com espaço opcional, conteúdo não-greedy
    processed = re.sub(r"\{\{\s*(.+?)\s*\}\}", replace_expr, source)

    return processed


def render_template(
    template_path: str,
    context: dict = None,
    router=None,
    static_root: str = "staticfiles",
) -> str:
    """
    Carrega um arquivo .html e renderiza com o engine do Vela.

    Args:
        template_path   Caminho relativo ao root do projeto
        context         Dicionário de variáveis
        router          Instância de Router (necessário para url())
        static_root     Diretório raiz dos estáticos

    Returns:
        String HTML processada.

    Raises:
        FileNotFoundError: se o template não existir

    Exemplo:
        html = render_template(
            "apps/dashboard/templates/index.html",
            {"user": "Dev"},
            router=router,
        )
    """
    context = context or {}

    full_path = os.path.join(os.getcwd(), template_path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Template não encontrado: {full_path}")

    with open(full_path, encoding="utf-8") as f:
        source = f.read()

    return render_string(source, context=context, router=router, static_root=static_root)
