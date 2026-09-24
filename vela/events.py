# SPDX-License-Identifier: MPL-2.0
"""Eventos Python -> JavaScript na janela Vela.

JS:
window.addEventListener("vela:event", event => {
    if (event.detail.name === "progresso") console.log(event.detail.payload)
});
"""
import json
from threading import RLock


class EventBus:
    def __init__(self):
        self._window = None
        self._subscribers = {}
        self._lock = RLock()

    def attach_window(self, window):
        """Injetado automaticamente quando o pywebview cria a janela."""
        with self._lock:
            self._window = window

    def on(self, name, listener):
        with self._lock:
            self._subscribers.setdefault(name, []).append(listener)

    def off(self, name, listener):
        with self._lock:
            if name in self._subscribers and listener in self._subscribers[name]:
                self._subscribers[name].remove(listener)

    def emit(self, name, payload=None):
        """Entrega callbacks Python e dispara CustomEvent("vela:event") no JS."""
        if not isinstance(name, str) or not name:
            raise ValueError("Nome do evento deve ser string nao vazia")
        detail = {"name": name, "payload": payload}
        js = "window.dispatchEvent(new CustomEvent('vela:event', {detail: " + (
            json.dumps(detail, ensure_ascii=False)) + "}));"
        with self._lock:
            listeners = tuple(self._subscribers.get(name, []))
            window = self._window
        for listener in listeners:
            listener(payload)
        if window is not None:
            window.evaluate_js(js)
        return detail


bus = EventBus()
