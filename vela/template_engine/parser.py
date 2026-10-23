# SPDX-License-Identifier: MPL-2.0
"""Lexer/parser pequeno e determinístico para templates Vela."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto

from vela.exceptions import TemplateSyntaxError
from vela.template_engine.nodes import ForNode, Node, StaticNode, TextNode, UrlNode, VariableNode


class TokenKind(Enum):
    TEXT = auto()
    VARIABLE = auto()
    URL = auto()
    STATIC = auto()
    FOR_START = auto()
    FOR_END = auto()


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    value: str


_CALL_RE = re.compile(r"^(url|static|for)\(\s*(['\"])(.*?)\2\s*\)$")
_NAME_RE = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")


def tokenize(source: str) -> tuple[Token, ...]:
    tokens: list[Token] = []
    cursor = 0
    while True:
        start = source.find("{{", cursor)
        if start < 0:
            if cursor < len(source):
                tokens.append(Token(TokenKind.TEXT, source[cursor:]))
            break
        if start > cursor:
            tokens.append(Token(TokenKind.TEXT, source[cursor:start]))
        end = source.find("}}", start + 2)
        if end < 0:
            raise TemplateSyntaxError("Expressão '{{' sem fechamento '}}'.")
        expression = source[start + 2 : end].strip()
        if expression == "endfor":
            tokens.append(Token(TokenKind.FOR_END, ""))
        else:
            call = _CALL_RE.fullmatch(expression)
            if call:
                kind = {
                    "url": TokenKind.URL,
                    "static": TokenKind.STATIC,
                    "for": TokenKind.FOR_START,
                }[call.group(1)]
                tokens.append(Token(kind, call.group(3)))
            elif _NAME_RE.fullmatch(expression):
                tokens.append(Token(TokenKind.VARIABLE, expression))
            else:
                tokens.append(
                    Token(
                        TokenKind.TEXT,
                        f"<!-- vela: expressão não suportada: {expression} -->",
                    )
                )
        cursor = end + 2
    return tuple(tokens)


def _parse_nodes(
    tokens: tuple[Token, ...], index: int = 0, *, nested: bool = False
) -> tuple[tuple[Node, ...], int]:
    nodes: list[Node] = []
    while index < len(tokens):
        token = tokens[index]
        if token.kind is TokenKind.FOR_END:
            if not nested:
                raise TemplateSyntaxError("'endfor' sem bloco 'for'.")
            return tuple(nodes), index + 1
        if token.kind is TokenKind.TEXT:
            nodes.append(TextNode(token.value))
        elif token.kind is TokenKind.VARIABLE:
            nodes.append(VariableNode(token.value))
        elif token.kind is TokenKind.URL:
            nodes.append(UrlNode(token.value))
        elif token.kind is TokenKind.STATIC:
            nodes.append(StaticNode(token.value))
        elif token.kind is TokenKind.FOR_START:
            children, index = _parse_nodes(tokens, index + 1, nested=True)
            nodes.append(ForNode(token.value, children))
            continue
        index += 1
    if nested:
        raise TemplateSyntaxError("Bloco 'for' sem 'endfor'.")
    return tuple(nodes), index


def parse(source: str) -> tuple[Node, ...]:
    nodes, _ = _parse_nodes(tokenize(source))
    return nodes
