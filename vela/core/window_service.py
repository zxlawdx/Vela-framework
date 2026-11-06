# SPDX-License-Identifier: MPL-2.0
"""Native fullscreen bridge with observable Qt/WinForms state.

pywebview's toggle_fullscreen() schedules a GUI change. Calling it successfully
does not mean that Qt/WinForms has actually entered fullscreen yet; inspect
the backend state before acknowledging a transition. Never use a cached intent
value as evidence that Windows has hidden its window decorations.
"""

from __future__ import annotations

from threading import RLock
from time import monotonic, sleep
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

    @staticmethod
    def _native_fullscreen(window: Any) -> bool | None:
        """Read the platform window, not merely pywebview's intended state.

        The Qt/WinForms backend changes its `is_fullscreen` flag on the
        GUI thread once the native operation has executed. Attribute lookup
        is read-only: this code never mutates GUI objects from a bridge worker.
        For unknown backends report unverified instead of guessing success.
        """
        if window is None:
            return None
        try:
            gui = getattr(window, "gui", None)
            uid = getattr(window, "uid", None)
            instances = getattr(getattr(gui, "BrowserView", None), "instances", None)
            if instances is None or uid is None:
                return None
            view = instances.get(uid)
            if view is None:
                return None
            if not hasattr(view, "is_fullscreen"):
                return None
            return bool(view.is_fullscreen)
        except (AttributeError, TypeError, RuntimeError):
            return None

    def get_state(self) -> dict[str, object]:
        with self._lock:
            window = self._window
            native = self._native_fullscreen(window)
            if native is not None:
                self._fullscreen = native
            return {
                "ok": window is not None,
                "available": window is not None,
                "fullscreen": self._fullscreen if native is None else native,
                "native_fullscreen": native,
                "verified": native is not None,
                "managed": True,
                "width": getattr(window, "width", None) if window else None,
                "height": getattr(window, "height", None) if window else None,
            }

    def set_fullscreen(self, enabled: bool) -> dict[str, object]:
        if type(enabled) is not bool:
            return {"ok": False, "error": "Fullscreen requer um valor booleano."}
        with self._lock:
            window = self._window
            if window is None:
                return {"ok": False, "error": "Janela desktop não disponível."}
            current = self._native_fullscreen(window)
            if current is None and self._fullscreen == enabled:
                # A previous unverified toggle cannot prove that the OS
                # actually reached the requested state.
                state = self.get_state()
                state.update(
                    ok=False, error="Estado fullscreen nativo indisponível para verificação."
                )
                return state
            if current is not None and current == enabled:
                self._fullscreen = enabled
                return self.get_state()
            toggle = getattr(window, "toggle_fullscreen", None)
            if not callable(toggle):
                return {"ok": False, "error": "Este backend não suporta fullscreen."}
            try:
                toggle()
            except Exception:
                return {"ok": False, "error": "Não foi possível alterar o modo de tela cheia."}

            # pywebview/Qt uses an asynchronous GUI signal. Poll the native
            # state (not the intent flag); do not retry by blindly toggling.
            deadline = monotonic() + 1.2
            observed = self._native_fullscreen(window)
            while observed is not None and observed != enabled and monotonic() < deadline:
                sleep(0.025)
                observed = self._native_fullscreen(window)
            if observed is None:
                self._fullscreen = enabled
                state = self.get_state()
                state.update(
                    ok=False,
                    verified=False,
                    error="Backend não informa o estado fullscreen real; alteração não confirmada.",
                )
                return state
            self._fullscreen = observed
            state = self.get_state()
            if observed != enabled:
                state.update(
                    ok=False,
                    error="A janela não atingiu o modo fullscreen solicitado.",
                )
            return state

    def toggle_fullscreen(self) -> dict[str, object]:
        with self._lock:
            current = self._native_fullscreen(self._window)
            return self.set_fullscreen(not (self._fullscreen if current is None else current))
