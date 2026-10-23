# SPDX-License-Identifier: MPL-2.0
"""Deterministic application lifecycle and idempotent shutdown."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from vela.log.logger import VelaLogger


class LifecycleState(str, Enum):
    CREATED = "created"
    CONFIGURED = "configured"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"


class LifecycleManager:
    _ALLOWED = {
        LifecycleState.CREATED: {LifecycleState.CONFIGURED, LifecycleState.STOPPING},
        LifecycleState.CONFIGURED: {LifecycleState.STARTING, LifecycleState.STOPPING},
        LifecycleState.STARTING: {LifecycleState.RUNNING, LifecycleState.STOPPING},
        LifecycleState.RUNNING: {LifecycleState.STOPPING},
        LifecycleState.STOPPING: {LifecycleState.STOPPED},
        LifecycleState.STOPPED: set(),
    }

    def __init__(self):
        self.state = LifecycleState.CREATED
        self._startup: list[Callable[[], object]] = []
        self._shutdown: list[Callable[[], object]] = []
        self.logger = VelaLogger("lifecycle")

    @property
    def phase(self) -> str:
        """Compatibility alias for older diagnostics."""
        return self.state.value

    def on_startup(self, callback: Callable[[], object]):
        if callback not in self._startup:
            self._startup.append(callback)
        return callback

    def on_shutdown(self, callback: Callable[[], object]):
        if callback not in self._shutdown:
            self._shutdown.append(callback)
        return callback

    def transition(self, state: LifecycleState | str) -> None:
        target = state if isinstance(state, LifecycleState) else LifecycleState(state)
        if target == self.state:
            return
        if target not in self._ALLOWED[self.state]:
            raise RuntimeError(f"Transição de lifecycle inválida: {self.state.value} -> {target.value}")
        self.state = target
        self.logger.debug(f"Lifecycle → {target.value}")

    def configured(self) -> None:
        self.transition(LifecycleState.CONFIGURED)

    def startup(self) -> None:
        if self.state is LifecycleState.CREATED:
            self.configured()
        self.transition(LifecycleState.STARTING)
        for callback in tuple(self._startup):
            callback()

    def running(self) -> None:
        self.transition(LifecycleState.RUNNING)

    def shutdown(self) -> None:
        if self.state is LifecycleState.STOPPED:
            return
        if self.state is not LifecycleState.STOPPING:
            self.transition(LifecycleState.STOPPING)
        for callback in reversed(tuple(self._shutdown)):
            try:
                callback()
            except Exception as exc:
                self.logger.exception(f"Erro durante shutdown: {exc}")
        self.transition(LifecycleState.STOPPED)
