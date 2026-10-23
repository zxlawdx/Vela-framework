# SPDX-License-Identifier: MPL-2.0
"""AST e renderer do template engine V2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from vela.template_engine.safe import escape_value


class RenderEnvironment(Protocol):
    router: Any
    static_root: str
    base_url: str | None

    def resolve_url(self, name: str) -> str: ...
    def resolve_static(self, path: str) -> str: ...


def resolve_value(expression: str, context: Mapping[str, Any]) -> Any:
    """Resolve nomes simples/dotted sem executar Python arbitrário."""
    parts = expression.split(".")
    if not parts or not parts[0]:
        return ""
    current: Any = context.get(parts[0], "")
    for part in parts[1:]:
        if isinstance(current, Mapping):
            current = current.get(part, "")
        else:
            current = getattr(current, part, "")
        if current is None:
            return ""
    return current


class Node(Protocol):
    def render(
        self, context: Mapping[str, Any], env: RenderEnvironment, parts: list[str]
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class TextNode:
    text: str

    def render(self, context: Mapping[str, Any], env: RenderEnvironment, parts: list[str]) -> None:
        parts.append(self.text)


@dataclass(frozen=True, slots=True)
class VariableNode:
    expression: str

    def render(self, context: Mapping[str, Any], env: RenderEnvironment, parts: list[str]) -> None:
        parts.append(escape_value(resolve_value(self.expression, context)))


@dataclass(frozen=True, slots=True)
class UrlNode:
    name: str

    def render(self, context: Mapping[str, Any], env: RenderEnvironment, parts: list[str]) -> None:
        parts.append(escape_value(env.resolve_url(self.name)))


@dataclass(frozen=True, slots=True)
class StaticNode:
    path: str

    def render(self, context: Mapping[str, Any], env: RenderEnvironment, parts: list[str]) -> None:
        parts.append(escape_value(env.resolve_static(self.path)))


@dataclass(frozen=True, slots=True)
class ForNode:
    collection: str
    children: tuple[Node, ...]

    def render(self, context: Mapping[str, Any], env: RenderEnvironment, parts: list[str]) -> None:
        items = resolve_value(self.collection, context)
        if items in (None, ""):
            return
        try:
            iterator = iter(items)
        except TypeError:
            return
        for item in iterator:
            child_context = dict(context)
            child_context["item"] = item
            for child in self.children:
                child.render(child_context, env, parts)
