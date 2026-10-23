# SPDX-License-Identifier: MPL-2.0
"""Hot reload seletivo baseado em mtime; nunca ativo em produção."""

from __future__ import annotations

import importlib
import os
import sys
from contextlib import nullcontext
from pathlib import Path
from types import ModuleType
from typing import Callable

from vela.log.logger import VelaLogger


class HotReloadManager:
    def __init__(self, enabled: bool = False):
        self.enabled = bool(enabled) and os.environ.get("VELA_PRODUCTION") != "1"
        self._tracked: dict[str, tuple[Path, int]] = {}
        self._callbacks: list[Callable[[str, ModuleType], None]] = []
        self._reload_context = None
        self.logger = VelaLogger("hotreload")

    def set_reload_context(self, factory) -> None:
        """Define context manager usado durante importlib.reload (ex.: API app-scoped)."""
        self._reload_context = factory

    def add_reload_callback(self, callback: Callable[[str, ModuleType], None]) -> None:
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def track_module(self, module: ModuleType) -> None:
        if not self.enabled:
            return
        filename = getattr(module, "__file__", None)
        if not filename:
            return
        path = Path(filename).resolve()
        try:
            mtime = path.stat().st_mtime_ns
        except OSError:
            return
        self._tracked[module.__name__] = (path, mtime)

    def track_loaded_prefix(self, prefix: str) -> None:
        if not self.enabled:
            return
        for name, module in tuple(sys.modules.items()):
            if module is not None and (name == prefix or name.startswith(prefix + ".")):
                self.track_module(module)

    def refresh(self) -> tuple[str, ...]:
        if not self.enabled:
            return ()
        dirty: list[str] = []
        for name, (path, previous_mtime) in tuple(self._tracked.items()):
            try:
                current_mtime = path.stat().st_mtime_ns
            except OSError:
                continue
            if current_mtime != previous_mtime:
                dirty.append(name)
        reloaded: list[str] = []
        for name in sorted(dirty, key=lambda value: value.count("."), reverse=True):
            module = sys.modules.get(name)
            if module is None:
                continue
            try:
                context = self._reload_context() if self._reload_context else nullcontext()
                with context:
                    module = importlib.reload(module)
                self.track_module(module)
                for callback in tuple(self._callbacks):
                    callback(name, module)
                reloaded.append(name)
                self.logger.info(f"Módulo recarregado: {name}")
            except Exception as exc:
                self.logger.exception(f"Falha no hot reload de {name}: {exc}")
        return tuple(reloaded)

    @property
    def tracked_modules(self) -> tuple[str, ...]:
        return tuple(self._tracked)
