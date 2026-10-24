# SPDX-License-Identifier: MPL-2.0
import re
import unittest
from pathlib import Path

SHELL = Path(__file__).resolve().parents[1] / "vela" / "core" / "shell.html"


class ShellIsolationRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shell = SHELL.read_text(encoding="utf-8")
        cls.style = cls.shell.split("<style>", 1)[1].split("</style>", 1)[0]
        cls.script = cls.shell.rsplit("<script>", 1)[1].split("</script>", 1)[0]

    def test_shell_has_explicit_application_boundary(self):
        self.assertIn('class="vela-shell"', self.shell)
        self.assertIn('id="vela-app-root"', self.shell)
        self.assertIn('class="vela-shell__app-root"', self.shell)

    def test_shell_does_not_disable_text_selection(self):
        self.assertNotIn("user-select: none", self.style)
        self.assertNotIn("-webkit-user-select: none", self.style)

    def test_shell_does_not_style_application_elements_globally(self):
        forbidden = (
            "*",
            "main",
            "dialog",
            "button",
            "canvas",
            "[contenteditable]",
            ".textLayer",
        )
        selectors = []
        for block in self.style.split("{")[:-1]:
            selector = block.rsplit("}", 1)[-1].strip()
            selectors.extend(part.strip() for part in selector.split(","))
        for item in forbidden:
            self.assertNotIn(item, selectors, f"global shell selector leaked: {item}")

    def test_shell_does_not_use_remote_assets(self):
        self.assertNotRegex(self.shell, r"https?://")
        self.assertNotIn("cdn.tailwindcss.com", self.shell)
        self.assertNotIn("fonts.googleapis.com", self.shell)

    def test_application_root_has_no_framework_padding_or_background(self):
        rule = re.search(r"\.vela-shell__app-root\s*\{([^}]*)\}", self.style, re.S)
        self.assertIsNotNone(rule)
        body = rule.group(1)
        self.assertIn("padding: 0", body)
        self.assertIn("background: transparent", body)
        self.assertNotIn("transform:", body)
        self.assertNotIn("filter:", body)
        self.assertNotIn("backdrop-filter:", body)
        self.assertNotIn("contain:", body)

    def test_disabled_shell_regions_are_removed_without_spacers(self):
        self.assertIn("document.getElementById('vela-sidebar')?.remove()", self.script)
        self.assertIn("document.getElementById('vela-topbar')?.remove()", self.script)

    def test_navigation_uses_generation_and_abort_controller(self):
        self.assertIn("_navigationGeneration", self.script)
        self.assertIn("new AbortController()", self.script)
        self.assertIn("controller.signal", self.script)
        self.assertIn("generation !== this._navigationGeneration", self.script)

    def test_page_lifecycle_has_four_hooks(self):
        for hook in ("beforeMount", "mounted", "beforeUnmount", "unmounted"):
            self.assertIn(hook, self.script)

    def test_page_links_use_one_delegated_listener(self):
        self.assertNotIn("bindPageLinks", self.script)
        self.assertEqual(self.script.count("document.addEventListener('click'"), 1)

    def test_inline_scripts_are_replaced_inside_page_not_appended_to_body(self):
        self.assertIn("oldScript.replaceWith(newScript)", self.script)
        self.assertNotIn("document.body.appendChild(newScript)", self.script)

    def test_clipboard_path_never_uses_navigator_clipboard(self):
        self.assertIn("clipboard_write_text", self.script)
        self.assertIn("document.execCommand('copy')", self.script)
        self.assertNotIn("navigator.clipboard", self.script)

    def test_capabilities_probe_real_browser_features(self):
        self.assertIn("'PointerEvent' in window", self.script)
        self.assertIn("getContext('webgl')", self.script)
        self.assertIn("getContext('webgl2')", self.script)
        self.assertIn("localStorage.setItem", self.script)

    def test_bootstrap_waits_for_real_pywebview_bridge_methods(self):
        self.assertIn("function velaBridgeReady()", self.script)
        self.assertIn("typeof api?.get_config === 'function'", self.script)
        self.assertIn("typeof api?.navigate === 'function'", self.script)
        self.assertNotIn("if (window.pywebview?.api) Vela.init()", self.script)
        self.assertIn("if (velaBridgeReady()) Vela.init()", self.script)

    def test_failed_or_concurrent_init_can_retry_safely(self):
        self.assertIn("_initializing: false", self.script)
        self.assertIn("if (this._initialized || this._initializing) return", self.script)
        self.assertIn("this._initializing = true", self.script)
        self.assertIn("this._initialized = false", self.script)
        self.assertIn("this._initializing = false", self.script)
        get_config_index = self.script.index("await window.pywebview.api.get_config()")
        navigate_index = self.script.index("await this.navigate(entry)")
        initialized_index = self.script.index("this._initialized = true", navigate_index)
        self.assertLess(get_config_index, navigate_index)
        self.assertLess(navigate_index, initialized_index)


if __name__ == "__main__":
    unittest.main()
