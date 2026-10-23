# SPDX-License-Identifier: MPL-2.0
"""Static asset contract shared by templates, runtime, build and diagnostics."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import quote

DEFAULT_RUNTIME_PREFIX = "/__vela__/static"
MANIFEST_NAME = "manifest.json"
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:/")


def _safe_relative(value: str | Path) -> Path:
    text = str(value).replace("\\", "/")
    candidate = Path(text)
    if (
        not text
        or text.startswith("/")
        or text.startswith("//")
        or candidate.is_absolute()
        or _WINDOWS_ABSOLUTE_RE.match(text)
        or ".." in candidate.parts
    ):
        raise ValueError(f"Caminho static inválido: {value!r}")
    if any(part in ("", ".") for part in candidate.parts):
        candidate = Path(*[part for part in candidate.parts if part not in ("", ".")])
    if not candidate.parts:
        raise ValueError("Caminho static vazio.")
    return candidate


def _within(target: Path, root: Path) -> bool:
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class StaticResolver:
    """Resolve source/collected assets without exposing internal URL details to apps."""

    project_root: Path
    source_roots: tuple[Path, ...]
    collected_root: Path
    runtime_prefix: str = DEFAULT_RUNTIME_PREFIX

    @classmethod
    def for_project(
        cls,
        project_root: str | Path = ".",
        *,
        source_roots: Sequence[str | Path] | None = None,
        collected_root: str | Path = "staticfiles",
        runtime_prefix: str = DEFAULT_RUNTIME_PREFIX,
    ) -> "StaticResolver":
        root = Path(project_root).resolve()
        sources = tuple(
            (root / source).resolve() if not Path(source).is_absolute() else Path(source).resolve()
            for source in (source_roots or ("static",))
        )
        collected = Path(collected_root)
        if not collected.is_absolute():
            collected = root / collected
        prefix = "/" + runtime_prefix.strip("/")
        return cls(root, sources, collected.resolve(), prefix)

    def relative(self, value: str | Path) -> Path:
        return _safe_relative(value)

    def url(self, value: str | Path, *, base_url: str | None = None) -> str:
        relative = self.relative(value).as_posix()
        encoded = "/".join(quote(part, safe="@:+,=-._~") for part in relative.split("/"))
        path = f"{self.runtime_prefix}/{encoded}"
        return f"{base_url.rstrip('/')}{path}" if base_url else path

    def resolve_collected(self, value: str | Path, *, must_exist: bool = True) -> Path:
        relative = self.relative(value)
        target = (self.collected_root / relative).resolve()
        if not _within(target, self.collected_root):
            raise ValueError("Static path escapou da collected root.")
        if must_exist and not target.is_file():
            raise FileNotFoundError(f"Asset coletado não encontrado: {relative.as_posix()}")
        return target

    def resolve_source(self, value: str | Path) -> Path:
        relative = self.relative(value)
        for root in self.source_roots:
            target = (root / relative).resolve()
            if not _within(target, root):
                continue
            if target.is_file():
                return target
        raise FileNotFoundError(f"Asset source não encontrado: {relative.as_posix()}")


@dataclass(frozen=True, slots=True)
class AssetManifest:
    root: Path
    files: dict[str, str]
    version: int = 2
    algorithm: str = "sha256"

    @classmethod
    def generate(cls, root: str | Path) -> "AssetManifest":
        base = Path(root).resolve()
        files: dict[str, str] = {}
        if base.exists():
            for path in sorted(base.rglob("*")):
                if (
                    not path.is_file()
                    or path.name == MANIFEST_NAME
                    or "__pycache__" in path.parts
                ):
                    continue
                files[path.relative_to(base).as_posix()] = _sha256(path)
        return cls(base, files)

    @classmethod
    def load(cls, root: str | Path) -> "AssetManifest":
        base = Path(root).resolve()
        path = base / MANIFEST_NAME
        data = json.loads(path.read_text(encoding="utf-8"))
        version = int(data.get("version", 1))
        algorithm = data.get("algorithm", "md5" if version == 1 else "sha256")
        return cls(base, dict(data.get("files") or {}), version=version, algorithm=algorithm)

    def write(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.root / MANIFEST_NAME
        target.write_text(
            json.dumps(
                {"version": self.version, "algorithm": self.algorithm, "files": self.files},
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return target

    def verify(self, required: Iterable[str] = ()) -> list[str]:
        errors: list[str] = []
        for item in required:
            relative = _safe_relative(item).as_posix()
            if relative not in self.files:
                errors.append(f"asset obrigatório ausente do manifest: {relative}")
        for relative, expected in self.files.items():
            try:
                target = StaticResolver.for_project(
                    self.root, collected_root=self.root
                ).resolve_collected(relative)
            except (ValueError, FileNotFoundError) as exc:
                errors.append(str(exc))
                continue
            if self.algorithm == "sha256":
                actual = _sha256(target)
                if actual != expected:
                    errors.append(f"hash divergente: {relative}")
        return errors
