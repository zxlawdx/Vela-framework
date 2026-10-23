# SPDX-License-Identifier: MPL-2.0
"""Lifecycle explícito e shutdown idempotente."""

from __future__ import annotations

from collections.abc import Callable

from vela.log.logger import VelaLogger


class LifecycleManager:
    PHASES = ("configure", "startup", "api_start", "window_start", "running", "shutdown")

    def __init__(self):
        self.phase = "configure"
        self._startup: list[Callable[[], object]] = []
        self._shutdown: list[Callable[[], object]] = []
        self._closed = False
        self.logger = VelaLogger("lifecycle")

    def on_startup(self, callback: Callable[[], object]):
        if callback not in self._startup:
            self._startup.append(callback)
        return callback

    def on_shutdown(self, callback: Callable[[], object]):
        if callback not in self._shutdown:
            self._shutdown.append(callback)
        return callback

    def transition(self, phase: str) -> None:
        if phase not in self.PHASES:
            raise ValueError(f"Fase de lifecycle desconhecida: {phase}")
        self.phase = phase
        self.logger.debug(f"Lifecycle → {phase}")

    def startup(self) -> None:
        self.transition("startup")
        for callback in tuple(self._startup):
            callback()

    def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.transition("shutdown")
        for callback in reversed(tuple(self._shutdown)):
            try:
                callback()
            except Exception as exc:
                self.logger.exception(f"Erro durante shutdown: {exc}")
