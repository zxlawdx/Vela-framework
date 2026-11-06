# SPDX-License-Identifier: MPL-2.0
"""Public fullscreen API regressions; no GUI assertion is mocked as native proof."""

import unittest
from threading import Timer
from types import SimpleNamespace
from unittest import mock

from vela.core.bridge import BaseBridge
from vela.core.window_service import NativeWindowService


class FakeWindow:
    width = 1440
    height = 900

    def __init__(self):
        self.toggles = 0
        self.scripts = []
        self.uid = 'fake-window'
        self.native = SimpleNamespace(is_fullscreen=False)
        self.gui = SimpleNamespace(BrowserView=SimpleNamespace(instances={self.uid: self.native}))

    def toggle_fullscreen(self):
        self.toggles += 1
        self.native.is_fullscreen = not self.native.is_fullscreen

    def evaluate_js(self, script):
        self.scripts.append(script)


class WindowServiceTests(unittest.TestCase):
    def test_not_attached_or_invalid_boolean(self):
        service = NativeWindowService()
        self.assertFalse(service.get_state()["available"])
        self.assertFalse(service.set_fullscreen(True)["ok"])
        window = FakeWindow()
        service.attach(window)
        self.assertFalse(service.set_fullscreen("true")["ok"])
        self.assertEqual(window.toggles, 0)

    def test_repeated_requests_idempotent_and_restoration(self):
        service = NativeWindowService()
        window = FakeWindow()
        service.attach(window)
        self.assertTrue(service.set_fullscreen(True)["fullscreen"])
        self.assertTrue(service.get_state()["verified"])
        self.assertTrue(service.set_fullscreen(True)["fullscreen"])
        self.assertEqual(window.toggles, 1)
        self.assertFalse(service.set_fullscreen(False)["fullscreen"])
        self.assertFalse(service.set_fullscreen(False)["fullscreen"])
        self.assertEqual(window.toggles, 2)

    def test_failure_does_not_corrupt_managed_state(self):
        service = NativeWindowService()
        window = FakeWindow()
        window.toggle_fullscreen = mock.Mock(side_effect=RuntimeError("test"))
        service.attach(window)
        self.assertFalse(service.set_fullscreen(True)["ok"])
        self.assertFalse(service.get_state()["fullscreen"])


    def test_delayed_native_signal_must_be_observed_before_success(self):
        service = NativeWindowService()
        window = FakeWindow()
        def delayed():
            window.toggles += 1
            Timer(0.06, lambda: setattr(window.native, 'is_fullscreen', True)).start()
        window.toggle_fullscreen = delayed
        service.attach(window)
        state = service.set_fullscreen(True)
        self.assertTrue(state["ok"])
        self.assertTrue(state["verified"])
        self.assertIs(state["native_fullscreen"], True)

    def test_os_refuses_fullscreen_is_not_reported_as_success(self):
        service = NativeWindowService()
        window = FakeWindow()
        window.toggle_fullscreen = lambda: None
        service.attach(window)
        state = service.set_fullscreen(True)
        self.assertFalse(state["ok"])
        self.assertFalse(state["fullscreen"])
        self.assertIs(state["native_fullscreen"], False)

    def test_unknown_backend_does_not_falsely_confirm_fullscreen(self):
        service = NativeWindowService()
        window = FakeWindow()
        window.gui = None
        service.attach(window)
        state = service.set_fullscreen(True)
        self.assertFalse(state["ok"])
        self.assertFalse(state["verified"])
        self.assertIsNone(state["native_fullscreen"])

    def test_bridge_propagates_events_and_detaches(self):
        bridge = BaseBridge()
        window = FakeWindow()
        bridge._attach_window(window)
        self.assertTrue(bridge.window_set_fullscreen(True)["fullscreen"])
        self.assertTrue(any("window:state" in script for script in window.scripts))
        self.assertFalse(bridge.window_toggle_fullscreen()["fullscreen"])
        self.assertEqual(window.toggles, 2)
        bridge._detach_window()
        self.assertFalse(bridge.window_get_state()["available"])
        self.assertFalse(bridge.window_set_fullscreen(True)["ok"])


if __name__ == "__main__":
    unittest.main()
