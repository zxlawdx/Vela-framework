# SPDX-License-Identifier: MPL-2.0
"""Template engine Vela: cached AST, autoescaping and shared static resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

from vela.exceptions import TemplateError
from vela.static import StaticResolver
from vela.template_engine.nodes import Node
from vela.template_engine.parser import parse


@dataclass(frozen=True, slots=True)
class _Environment:
    router: Any
    static_root: str
    base_url: str | None

    def resolve_url(self, name: str) -> str:
        if self.router is None:
            return f"/#url-not-resolved-{name}"
        try:
            return self.router.url_for(name)
        except KeyError:
            return f"/#route-{name}-not-found"

    def resolve_static(self, path: str) -> str:
        try:
            resolver = StaticResolver.for_project(collected_root=self.static_root)
            if self.base_url:
                return resolver.url(path, base_url=self.base_url)
            return resolver.resolve_collected(path, must_exist=False).as_uri()
        except ValueError as exc:
            raise TemplateError("Caminho de asset inválido.") from exc


@dataclass(frozen=True, slots=True)
class CompiledTemplate:
    nodes: tuple[Node, ...]

    def render(
        self,
        context: Mapping[str, Any],
        router=None,
        static_root: str = "staticfiles",
    ) -> str:
        base_url = context.get("__base_url__") if isinstance(context, Mapping) else None
        if not base_url and router is not None:
            base_url = getattr(router, "base_url", None)
        env = _Environment(router=router, static_root=static_root, base_url=base_url)
        parts: list[str] = []
        for node in self.nodes:
            node.render(context, env, parts)
        return "".join(parts)


def compile_template(source: str) -> CompiledTemplate:
    return CompiledTemplate(parse(source))


def _ensure_within(path: Path, roots: Sequence[Path], kind: str) -> Path:
    for root in roots:
        try:
            path.relative_to(root)
            return path
        except ValueError:
            continue
    raise TemplateError(f"Caminho de {kind} fora das roots permitidas: {path}")


def _template_roots(
    template_roots: Sequence[str | os.PathLike[str]] | None,
) -> tuple[Path, ...]:
    roots = template_roots or (Path.cwd(),)
    return tuple(Path(root).resolve() for root in roots)


def _resolve_template_path(
    template_path: str | os.PathLike[str],
    template_roots: Sequence[str | os.PathLike[str]] | None = None,
) -> Path:
    roots = _template_roots(template_roots)
    raw = Path(template_path)
    candidate = raw.resolve() if raw.is_absolute() else (Path.cwd() / raw).resolve()
    return _ensure_within(candidate, roots, "template")


@lru_cache(maxsize=256)
def _read_template_cached(path: str, mtime_ns: int, size: int) -> str:
    return Path(path).read_text(encoding="utf-8")


@lru_cache(maxsize=256)
def _compile_template_cached(path: str, mtime_ns: int, size: int) -> CompiledTemplate:
    source = _read_template_cached(path, mtime_ns, size)
    return compile_template(source)


def clear_template_cache() -> None:
    _read_template_cached.cache_clear()
    _compile_template_cached.cache_clear()


def render_string(
    source: str,
    context: Mapping[str, Any] | None = None,
    router=None,
    static_root: str = "staticfiles",
) -> str:
    return compile_template(source).render(context or {}, router=router, static_root=static_root)


def render_template(
    template_path: str,
    context: Mapping[str, Any] | None = None,
    router=None,
    static_root: str = "staticfiles",
    template_roots: Sequence[str | os.PathLike[str]] | None = None,
) -> str:
    path = _resolve_template_path(template_path, template_roots)
    if not path.is_file():
        raise FileNotFoundError(f"Template não encontrado: {path}")
    metadata = path.stat()
    compiled = _compile_template_cached(str(path), metadata.st_mtime_ns, metadata.st_size)
    return compiled.render(context or {}, router=router, static_root=static_root)
