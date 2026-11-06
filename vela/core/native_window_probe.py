# SPDX-License-Identifier: MPL-2.0
"""Backend window probes: observe real Qt/WinForms state on the owning UI thread.

Return None when unavailable. A pywebview is_fullscreen flag alone is NOT
accepted as evidence that the operating-system window covers its display.
"""

from __future__ import annotations

import os
from threading import Event


def _covers_screen(bounds, screen, tolerance=5):
    """Compare actual top-level window rectangle with display geometry."""
    x, y, width, height = bounds
    sx, sy, sw, sh = screen
    return (
        sw > 0
        and sh > 0
        and abs(x - sx) <= tolerance
        and abs(y - sy) <= tolerance
        and abs(width - sw) <= tolerance
        and abs(height - sh) <= tolerance
    )


def qt_client_bounds(view):
    """Visible content bounds in monitor coordinates, not Qt frame shadows.

    Windows adds an invisible resize border to frameGeometry even for a
    fullscreen window. GetClientRect + ClientToScreen reads the actual native
    HWND content extent. This still demands exact coverage of the display.
    """
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class Rect(ctypes.Structure):
                _fields_ = [
                    ("left", wintypes.LONG),
                    ("top", wintypes.LONG),
                    ("right", wintypes.LONG),
                    ("bottom", wintypes.LONG),
                ]

            hwnd = int(view.winId())
            rect = Rect()
            point = wintypes.POINT(0, 0)
            user32 = ctypes.windll.user32
            if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
                return None
            if not user32.ClientToScreen(hwnd, ctypes.byref(point)):
                return None
            return (
                point.x,
                point.y,
                rect.right - rect.left,
                rect.bottom - rect.top,
            )
        from qtpy.QtCore import QPoint

        p = view.mapToGlobal(QPoint(0, 0))
        size = view.size()
        return p.x(), p.y(), size.width(), size.height()
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
        return None


def qt_fullscreen(view):
    """Probe a QMainWindow on its GUI thread, never a worker thread."""
    try:
        from qtpy.QtCore import QObject, Qt, QThread, Signal, Slot
        from qtpy.QtWidgets import QApplication
    except ImportError:
        return None

    app = QApplication.instance()
    if app is None:
        return None

    class Inspector(QObject):
        request = Signal()

        def __init__(self):
            super().__init__()
            self.done = Event()
            self.result = None
            self.request.connect(self.sample)

        @Slot()
        def sample(self):
            try:
                screen_obj = view.screen()
                if screen_obj is None:
                    return
                display = screen_obj.geometry()
                bounds = qt_client_bounds(view)
                screen = (display.x(), display.y(), display.width(), display.height())
                full_state = bool(view.windowState() & Qt.WindowFullScreen)
                self.result = bool(
                    view.isFullScreen()
                    and full_state
                    and bounds is not None
                    and _covers_screen(bounds, screen)
                )
            except (AttributeError, RuntimeError, TypeError):
                self.result = None
            finally:
                self.done.set()

    inspector = Inspector()
    if QThread.currentThread() == app.thread():
        inspector.sample()
    else:
        inspector.moveToThread(app.thread())
        inspector.request.emit()
        if not inspector.done.wait(0.65):
            return None
    return inspector.result


def winforms_fullscreen(view):
    """Query actual Form bounds and border style via Control.Invoke."""
    try:
        from System import Boolean, Func
        from System.Windows.Forms import (
            FormBorderStyle,
            FormWindowState,
            Screen,
        )
    except ImportError:
        return None

    def read():
        try:
            actual = view.Bounds
            monitor = Screen.FromControl(view).Bounds
            bounds = (actual.X, actual.Y, actual.Width, actual.Height)
            screen = (monitor.X, monitor.Y, monitor.Width, monitor.Height)
            return bool(
                view.FormBorderStyle == getattr(FormBorderStyle, "None")
                and view.WindowState == FormWindowState.Maximized
                and _covers_screen(bounds, screen)
            )
        except (AttributeError, RuntimeError, TypeError):
            return False

    try:
        if view.InvokeRequired:
            return bool(view.Invoke(Func[Boolean](read)))
        return read()
    except Exception:
        return None


def native_fullscreen(window):
    """Return verified OS state, not cached intent or backend bookkeeping."""
    if window is None:
        return None
    try:
        backend = getattr(window, "gui", None)
        uid = getattr(window, "uid", None)
        instances = getattr(getattr(backend, "BrowserView", None), "instances", None)
        if instances is None or uid is None:
            return None
        view = instances.get(uid)
        if view is None:
            return None
        if callable(getattr(view, "isFullScreen", None)):
            return qt_fullscreen(view)
        if hasattr(view, "FormBorderStyle"):
            return winforms_fullscreen(view)
    except (AttributeError, TypeError, RuntimeError):
        pass
    return None
