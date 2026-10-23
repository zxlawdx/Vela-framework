# SPDX-License-Identifier: MPL-2.0
"""Selective hot reload with explicit persistent-module protection."""

from __future__ import annotations

import importlib
import os
import sys
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Callable

from vela.log.logger import VelaLogger


@dataclass(slots=True)
class WatchedModule:
    name: str
    path: Path
    mtime_ns: int
    reloadable: bool = True


class FileWatcher:
    @staticmethod
    def mtime(path: Path) -> int | None:
        try:
            return path.stat().st_mtime_ns
        except OSError:
            return None

    def changed(self, item: WatchedModule) -> bool:
        current = self.mtime(item.path)
        return current is not None and current != item.mtime_ns


class DirtyModuleRegistry:
    def __init__(self) -> None:
        self._items: dict[str, WatchedModule] = {}
        self._persistent_prefixes: set[str] = set()

    def protect(self, prefix: str) -> None:
        if prefix:
            self._persistent_prefixes.add(prefix)
            for item in self._items.values():
                if item.name == prefix or item.name.startswith(prefix + "."):
                    item.reloadable = False

    def is_protected(self, name: str) -> bool:
        return any(name == prefix or name.startswith(prefix + ".") for prefix in self._persistent_prefixes)

    def track(self, module: ModuleType, *, reloadable: bool = True) -> None:
        filename = getattr(module, "__file__", None)
        if not filename:
            return
        path = Path(filename).resolve()
        mtime = FileWatcher.mtime(path)
        if mtime is None:
            return
        self._items[module.__name__] = WatchedModule(
            module.__name__, path, mtime, reloadable and not self.is_protected(module.__name__)
        )

    def values(self):
        return tuple(self._items.values())

    def clear(self) -> None:
        self._items.clear()


class HotReloadManager:
    def __init__(self, enabled: bool = False):
        self.enabled = bool(enabled) and os.environ.get("VELA_PRODUCTION") != "1"
        self.registry = DirtyModuleRegistry()
        self.watcher = FileWatcher()
        self._callbacks: list[Callable[[str, ModuleType], None]] = []
        self._reload_context = None
        self.logger = VelaLogger("hotreload")

    def set_reload_context(self, factory) -> None:
        self._reload_context = factory

    def add_reload_callback(self, callback: Callable[[str, ModuleType], None]) -> None:
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def protect_prefix(self, prefix: str) -> None:
        self.registry.protect(prefix)

    def track_module(self, module: ModuleType, *, reloadable: bool = True) -> None:
        if self.enabled:
            self.registry.track(module, reloadable=reloadable)

    def track_loaded_prefix(self, prefix: str, *, reloadable: bool = False) -> None:
        """Compatibility helper; broad prefixes are persistent unless opted in."""
        if not self.enabled:
            return
        for name, module in tuple(sys.modules.items()):
            if module is not None and (name == prefix or name.startswith(prefix + ".")):
                self.track_module(module, reloadable=reloadable)

    def refresh(self) -> tuple[str, ...]:
        if not self.enabled:
            return ()
        dirty = [item for item in self.registry.values() if item.reloadable and self.watcher.changed(item)]
        reloaded: list[str] = []
        for item in sorted(dirty, key=lambda value: value.name.count("."), reverse=True):
            module = sys.modules.get(item.name)
            if module is None:
                continue
            try:
                context = self._reload_context() if self._reload_context else nullcontext()
                with context:
                    module = importlib.reload(module)
                self.registry.track(module, reloadable=True)
                for callback in tuple(self._callbacks):
                    callback(item.name, module)
                reloaded.append(item.name)
                self.logger.info(f"Módulo recarregado: {item.name}")
            except Exception as exc:
                self.logger.exception(f"Falha no hot reload de {item.name}: {exc}")
        return tuple(reloaded)

    def stop(self) -> None:
        self.registry.clear()

    @property
    def tracked_modules(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.registry.values())

    @property
    def _tracked(self) -> dict[str, tuple[Path, int]]:
        """Read-only compatibility view used by older test/tooling code."""
        return {item.name: (item.path, item.mtime_ns) for item in self.registry.values()}
