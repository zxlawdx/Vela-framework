"""
vela.template_engine.engine
Engine de templates do Vela.

Permite carregar arquivos .html de dentro da pasta templates/ de um app
e substituir variáveis no formato {{ variavel }}.

Uso:
    from vela.template_engine.engine import render_template

    html = render_template("apps/dashboard/templates/index.html", {
        "title": "Dashboard",
        "count": 42,
    })
"""

import os
import re


def render_template(template_path: str, context: dict = None) -> str:
    """
    Carrega um arquivo HTML e substitui variáveis {{ chave }} pelos valores do context.

    Args:
        template_path: Caminho para o arquivo .html (relativo ao root do projeto).
        context: Dicionário de variáveis a substituir no template.

    Returns:
        String HTML com as variáveis substituídas.

    Raises:
        FileNotFoundError: Se o template não existir.
    """
    context = context or {}

    full_path = os.path.join(os.getcwd(), template_path)
    
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Template não encontrado: {full_path}")

    with open(full_path, encoding="utf-8") as f:
        html = f.read()

    # Substitui {{ variavel }} pelo valor correspondente do context
    def replace_var(match):
        key = match.group(1).strip()
        value = context.get(key, "")
        return str(value)

    html = re.sub(r"\{\{\s*(\w+)\s*\}\}", replace_var, html)
    return html
