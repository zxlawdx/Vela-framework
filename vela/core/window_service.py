# SPDX-License-Identifier: MPL-2.0
"""Stateful and thread-safe pywebview window operations shared by Vela apps.

pywebview exposes toggle_fullscreen(), but not a portable fullscreen getter.
The service tracks changes made through this API. External/native shortcut
changes cannot be inferred and must not be reported as authoritative.
"""

from __future__ import annotations

from threading import RLock
from typing import Any


class NativeWindowService:
    def __init__(self) -> None:
        self._lock = RLock()
        self._window: Any = None
        self._fullscreen = False

    def attach(self, window: Any) -> None:
        with self._lock:
            self._window = window
            self._fullscreen = False

    def detach(self) -> None:
        with self._lock:
            self._window = None
            self._fullscreen = False

    def get_state(self) -> dict[str, object]:
        with self._lock:
            window = self._window
            return {
                "ok": window is not None,
                "available": window is not None,
                "fullscreen": self._fullscreen,
                "managed": True,
                "width": getattr(window, "width", None) if window else None,
                "height": getattr(window, "height", None) if window else None,
            }

    def set_fullscreen(self, enabled: bool) -> dict[str, object]:
        if type(enabled) is not bool:
            return {"ok": False, "error": "Fullscreen requer um valor booleano."}
        with self._lock:
            if self._window is None:
                return {"ok": False, "error": "Janela desktop não disponível."}
            if self._fullscreen == enabled:
                return self.get_state()
            toggle = getattr(self._window, "toggle_fullscreen", None)
            if not callable(toggle):
                return {"ok": False, "error": "Este backend não suporta fullscreen."}
            try:
                # pywebview marshals native calls into its active GUI backend.
                toggle()
            except Exception:
                return {"ok": False, "error": "Não foi possível alterar o modo de tela cheia."}
            self._fullscreen = enabled
            return self.get_state()

    def toggle_fullscreen(self) -> dict[str, object]:
        with self._lock:
            return self.set_fullscreen(not self._fullscreen)
