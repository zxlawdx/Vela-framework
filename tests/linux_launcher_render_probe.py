"""Exercise generated launcher defaults and sample the native X11 window."""

import json
import os
from pathlib import Path

from vela.cli.build import launcher_source

# Apply precisely the generated setup, before importing Qt. The test runner
# supplies DISPLAY and, only when necessary in a root container, sandbox policy.
prefix = launcher_source("qt5", os.environ.get("PROBE_COMPATIBILITY") == "1").split(
    '    if GUI == "qt6":', 1
)[0]
exec(compile(prefix, "generated-launcher-prefix", "exec"), {})

from qtpy.QtCore import QTimer, QUrl
from qtpy.QtWidgets import QApplication
from qtpy.QtWebEngineWidgets import QWebEngineView

output = Path(os.environ.get("GUI_ARTIFACT_DIR", "artifacts"))
output.mkdir(parents=True, exist_ok=True)
app = QApplication([])
view = QWebEngineView()
view.resize(800, 500)
state = {"loaded": False, "javascript": False, "native_pixels": False}


def finish():
    # Capture the native window, not Page.captureScreenshot or QWidget.render:
    # a healthy DOM alone does not prove that the compositor painted the window.
    image = view.screen().grabWindow(int(view.winId())).toImage()
    image.save(str(output / "launcher-native.png"))
    if not image.isNull():
        pixel = image.pixelColor(image.width() // 2, image.height() // 2)
        state["rgb"] = [pixel.red(), pixel.green(), pixel.blue()]
        state["native_pixels"] = pixel.green() > 140 and pixel.red() < 80
    state["gl_integration"] = os.environ.get("QT_XCB_GL_INTEGRATION", "auto")
    (output / "launcher-result.json").write_text(json.dumps(state, indent=2))
    print(json.dumps(state), flush=True)
    app.exit(0 if all(state[k] for k in ("loaded", "javascript", "native_pixels")) else 1)


def loaded(ok):
    state["loaded"] = bool(ok)
    view.page().runJavaScript(
        "document.body.dataset.ready === 'yes'",
        lambda ready: (state.update(javascript=bool(ready)), QTimer.singleShot(1000, finish)),
    )


view.loadFinished.connect(loaded)
view.setHtml(
    '<body style="margin:0;background:rgb(22,199,132)">'
    '<script>document.body.dataset.ready="yes"</script></body>',
    QUrl("about:blank"),
)
view.show()
QTimer.singleShot(20000, finish)
app.exec_()
raise SystemExit(0 if all(state[k] for k in ("loaded", "javascript", "native_pixels")) else 1)
