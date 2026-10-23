# SPDX-License-Identifier: MPL-2.0
"""Runtime self-check that avoids touching consumer implementation details."""

from __future__ import annotations

import json
import platform
import urllib.request
from pathlib import Path

from vela.core.api_router import ApiRouter
from vela.core.api_server import ApiServer
from vela.core.bridge import BaseBridge
from vela.core.router import Router
from vela.platform import PlatformServices


def run_self_test() -> dict[str, object]:
    checks: dict[str, object] = {}
    import vela

    checks["python"] = platform.python_version()
    checks["vela"] = vela.__version__
    shell = Path(__file__).resolve().parents[1] / "core" / "shell.html"
    text = shell.read_text(encoding="utf-8")
    checks["shell"] = shell.is_file()
    checks["offline_shell"] = "https://" not in text and "http://" not in text
    checks["js_contract"] = all(
        marker in text
        for marker in (
            "async capabilities()",
            "clipboard_write_text",
            "PointerEvent",
            "getContext('webgl')",
            "localStorage.setItem",
            "AbortController",
        )
    )

    router = Router()
    router.add("/self-test", lambda params: "<p>ok</p>")
    bridge = BaseBridge(router=router, platform=PlatformServices.detect())
    checks["bridge"] = bridge.ping() == "pong" and bridge.navigate("/self-test")["ok"]
    checks["capabilities"] = bridge.capabilities()

    server = ApiServer(ApiRouter(), port=0, server="bottle", docs_enabled=False)
    port = server.start()
    try:
        server.wait_until_ready(timeout=2)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as response:
            checks["http"] = json.loads(response.read())["ok"] is True
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/__vela__/shell", timeout=2
        ) as response:
            checks["static_shell"] = b"vela-app-root" in response.read()
    finally:
        server.stop()
    checks["shutdown"] = ApiServer.is_port_available("127.0.0.1", port)
    checks["ok"] = all(
        bool(checks[key])
        for key in (
            "shell",
            "offline_shell",
            "js_contract",
            "bridge",
            "http",
            "static_shell",
            "shutdown",
        )
    )
    return checks
