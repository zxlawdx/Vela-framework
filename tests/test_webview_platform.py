# SPDX-License-Identifier: MPL-2.0
import unittest
from unittest import mock

from vela.core.bridge import BaseBridge
from vela.core.router import Router
from vela.platform import ClipboardService, PlatformServices


class FakeClipboard:
    available = True

    def __init__(self):
        self.values = []

    def write_text(self, text):
        self.values.append(text)
        return True


class WebViewPlatformRegressionTests(unittest.TestCase):
    def test_bridge_clipboard_uses_native_service(self):
        clipboard = FakeClipboard()
        platform = PlatformServices(clipboard=clipboard, webview_backend="qt")
        bridge = BaseBridge(router=Router(), platform=platform)
        self.assertEqual(bridge.clipboard_write_text("ONT-123"), {"ok": True})
        self.assertEqual(clipboard.values, ["ONT-123"])

    def test_capabilities_do_not_invent_gpu_or_pointer_support(self):
        platform = PlatformServices(clipboard=FakeClipboard(), webview_backend="qt")
        caps = platform.capabilities()
        self.assertEqual(caps["webview"], "qt")
        self.assertTrue(caps["clipboard"])
        self.assertNotIn("webgl", caps)
        self.assertNotIn("pointerEvents", caps)

    def test_unknown_backend_is_reported_honestly(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(PlatformServices.detect().webview_backend, "unknown")

    def test_linux_clipboard_subprocess_is_shell_false(self):
        service = ClipboardService(platform_name="linux")
        completed = mock.Mock(returncode=0)
        with (
            mock.patch(
                "vela.platform.shutil.which",
                side_effect=lambda name: "/usr/bin/wl-copy" if name == "wl-copy" else None,
            ),
            mock.patch("vela.platform.subprocess.run", return_value=completed) as run,
        ):
            self.assertTrue(service.write_text("hello"))
        self.assertEqual(run.call_args.args[0], ["wl-copy"])
        self.assertFalse(run.call_args.kwargs["shell"])

    def test_bridge_rejects_huge_clipboard_payload(self):
        bridge = BaseBridge(router=Router(), platform=PlatformServices(FakeClipboard(), "qt"))
        result = bridge.clipboard_write_text("x" * (2 * 1024 * 1024 + 1))
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
