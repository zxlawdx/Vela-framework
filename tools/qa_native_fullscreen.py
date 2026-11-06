# SPDX-License-Identifier: MPL-2.0
"""Native Qt screenshot/geometry contract, executed with an actual QMainWindow.

Unlike the mock-based service tests, this program launches a real Qt event
loop, enters fullscreen, verifies widget state and screen bounds, captures
a screenshot, then restores the original window. A virtual/offscreen Qt
platform is reported explicitly and is NOT proof of OS fullscreen.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QLabel, QMainWindow

from vela.core.native_window_probe import qt_client_bounds, qt_fullscreen


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    screen = app.primaryScreen()
    if screen is None:
        raise RuntimeError("Nenhum monitor Qt disponível.")
    view = QMainWindow()
    view.setWindowTitle("Vela Native Fullscreen QA")
    content = QLabel("VELA QT FULLSCREEN — CAPTURA REAL")
    content.setAlignment(Qt.AlignCenter)
    content.setStyleSheet("QLabel{font-size:30px;background:#192f52;color:white;}")
    view.setCentralWidget(content)
    view.setGeometry(100, 100, 900, 600)
    view.showNormal()
    app.processEvents()
    previous = view.normalGeometry()
    assert not view.isFullScreen(), "A janela deve iniciar em modo normal."

    view.showFullScreen()
    start = time.monotonic()
    while time.monotonic() - start < 2.0:
        app.processEvents()
        if qt_fullscreen(view) is True:
            break
        time.sleep(0.025)

    result = {
        "qt_platform": app.platformName(),
        "os": os.name,
        "screen": [
            screen.geometry().x(),
            screen.geometry().y(),
            screen.geometry().width(),
            screen.geometry().height(),
        ],
        "native_is_fullscreen": view.isFullScreen(),
        "window_state_fullscreen": bool(view.windowState() & Qt.WindowFullScreen),
        "bounds": [
            view.frameGeometry().x(),
            view.frameGeometry().y(),
            view.frameGeometry().width(),
            view.frameGeometry().height(),
        ],
        "client_bounds": qt_client_bounds(view),
        "geometry": [
            view.geometry().x(),
            view.geometry().y(),
            view.geometry().width(),
            view.geometry().height(),
        ],
        "native_geometry_verified": qt_fullscreen(view),
    }
    destination = Path("docs/images/qa-native-fullscreen")
    destination.mkdir(parents=True, exist_ok=True)
    screenshot = destination / (
        "windows-qt-fullscreen.png" if os.name == "nt" else "linux-qt-fullscreen.png"
    )
    if not screen.grabWindow(0).save(str(screenshot)):
        screenshot = destination / "window-grab.png"
        if not view.grab().save(str(screenshot)):
            raise RuntimeError("Qt não conseguiu capturar a tela.")
    print("VELA_NATIVE_QT_FULLSCREEN_SCREENSHOT", screenshot)
    print("VELA_NATIVE_QT_FULLSCREEN_STATE", json.dumps(result))
    if result["native_geometry_verified"] is not True:
        raise AssertionError("Qt não comprovou fullscreen real pelo monitor.")

    view.showNormal()
    start = time.monotonic()
    while time.monotonic() - start < 2.0:
        app.processEvents()
        if not view.isFullScreen():
            break
        time.sleep(0.025)
    assert qt_fullscreen(view) is False, "A janela permaneceu fullscreen."
    restored = view.frameGeometry()
    assert (
        abs(restored.width() - previous.width()) <= 8
        and abs(restored.height() - previous.height()) <= 8
    ), "A geometria original da janela não foi restaurada."
    print("VELA_NATIVE_QT_FULLSCREEN_RESTORE_OK")
    view.close()
    app.quit()


if __name__ == "__main__":
    main()
