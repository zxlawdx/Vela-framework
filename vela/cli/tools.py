# SPDX-License-Identifier: MPL-2.0
"""Portable subprocess executable discovery for Vela build tooling."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def executable_candidates(
    name: str,
    *,
    project_root: str | Path | None = None,
    platform_name: str | None = None,
) -> list[str]:
    platform_name = platform_name or sys.platform
    windows = platform_name.startswith("win")
    candidates: list[str] = []
    root = Path(project_root).resolve() if project_root else None

    if root is not None:
        local = root / "node_modules" / ".bin"
        if windows:
            # npm creates POSIX shims and .cmd launchers side by side. Executing
            # the POSIX shim directly on Windows is the historical WinError 193.
            for suffix in (".cmd", ".exe", ".bat"):
                candidates.append(str(local / f"{name}{suffix}"))
        else:
            candidates.append(str(local / name))

    lookup_names = [name]
    if windows and Path(name).suffix.lower() not in {".cmd", ".exe", ".bat"}:
        lookup_names = [f"{name}.cmd", f"{name}.exe", f"{name}.bat", name]
    for lookup in lookup_names:
        resolved = shutil.which(lookup)
        if resolved:
            candidates.append(resolved)

    seen: set[str] = set()
    return [value for value in candidates if not (value in seen or seen.add(value))]


def resolve_executable(
    name: str,
    *,
    project_root: str | Path | None = None,
    platform_name: str | None = None,
) -> str | None:
    windows = (platform_name or sys.platform).startswith("win")
    for candidate in executable_candidates(
        name, project_root=project_root, platform_name=platform_name
    ):
        path = Path(candidate)
        if not path.exists():
            continue
        if windows and path.parent.name == ".bin" and path.suffix.lower() not in {
            ".cmd",
            ".exe",
            ".bat",
        }:
            continue
        if windows or os.access(path, os.X_OK):
            return str(path)
    return None


def resolve_node_tool(
    name: str, *, project_root: str | Path | None = None, platform_name: str | None = None
) -> str | None:
    return resolve_executable(
        name, project_root=project_root, platform_name=platform_name
    )
