# SPDX-License-Identifier: MPL-2.0
"""Event bus app-scoped para callbacks Python e eventos da WebView."""

from __future__ import annotations

import json
from threading import RLock
from typing import Any, Callable

from vela.log.logger import VelaLogger


class EventBus:
    def __init__(self):
        self._window = None
        self._subscribers: dict[str, list[Callable[[Any], object]]] = {}
        self._lock = RLock()
        self.logger = VelaLogger("events")

    def attach_window(self, window):
        with self._lock:
            self._window = window

    def on(self, name: str, listener: Callable[[Any], object]):
        if not isinstance(name, str) or not name:
            raise ValueError("Nome do evento deve ser string não vazia.")
        if not callable(listener):
            raise TypeError("Listener deve ser chamável.")
        with self._lock:
            listeners = self._subscribers.setdefault(name, [])
            if listener not in listeners:
                listeners.append(listener)
        return listener

    def off(self, name: str, listener: Callable[[Any], object]) -> bool:
        with self._lock:
            listeners = self._subscribers.get(name)
            if not listeners or listener not in listeners:
                return False
            listeners.remove(listener)
            if not listeners:
                self._subscribers.pop(name, None)
            return True

    def emit(self, name: str, payload: Any = None):
        if not isinstance(name, str) or not name:
            raise ValueError("Nome do evento deve ser string não vazia.")
        detail = {"name": name, "payload": payload}
        try:
            encoded = json.dumps(detail, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise TypeError(f"Payload do evento {name!r} não é serializável em JSON.") from exc
        js = f"window.dispatchEvent(new CustomEvent('vela:event', {{detail: {encoded}}}));"
        with self._lock:
            listeners = tuple(self._subscribers.get(name, ()))
            window = self._window
        for listener in listeners:
            try:
                listener(payload)
            except Exception as exc:
                self.logger.exception(f"Listener do evento {name!r} falhou: {exc}")
        if window is not None:
            try:
                window.evaluate_js(js)
            except Exception as exc:
                self.logger.exception(f"Falha ao emitir {name!r} para a WebView: {exc}")
        return detail

    def clear(self) -> None:
        with self._lock:
            self._subscribers.clear()
            self._window = None


bus = EventBus()
