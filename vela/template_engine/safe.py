# SPDX-License-Identifier: MPL-2.0
"""Primitivas de confiança e escaping do template engine."""
from __future__ import annotations

from html import escape
from typing import Any


class SafeHTML(str):
    """HTML explicitamente marcado como confiável pela aplicação.

    Nunca use ``mark_safe`` com entrada de usuário, rede, arquivo não confiável
    ou qualquer valor que não esteja sob controle da aplicação.
    """


def mark_safe(value: Any) -> SafeHTML:
    """Marca HTML confiável para bypass explícito do autoescaping."""
    return SafeHTML(str(value))


def escape_value(value: Any) -> str:
    """Converte um valor para HTML aplicando escaping por padrão."""
    if value is None:
        return ""
    if isinstance(value, SafeHTML):
        return str(value)
    return escape(str(value), quote=True)
