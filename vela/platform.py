# SPDX-License-Identifier: MPL-2.0
"""Small native platform surface exposed safely to Vela applications."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass


class ClipboardService:
    """Native clipboard writer with no dependency on ``navigator.clipboard``."""

    def __init__(self, platform_name: str | None = None):
        self.platform_name = platform_name or sys.platform

    @property
    def available(self) -> bool:
        if self.platform_name.startswith("win"):
            try:
                import ctypes

                return bool(ctypes.windll.user32.OpenClipboard)
            except (AttributeError, OSError):
                return False
        if self.platform_name == "darwin":
            return shutil.which("pbcopy") is not None
        return any(shutil.which(name) for name in ("wl-copy", "xclip", "xsel"))

    def write_text(self, text: str) -> bool:
        value = str(text)
        if self.platform_name.startswith("win"):
            return self._write_windows(value)
        if self.platform_name == "darwin":
            return self._pipe(["pbcopy"], value)
        if shutil.which("wl-copy"):
            return self._pipe(["wl-copy"], value)
        if shutil.which("xclip"):
            return self._pipe(["xclip", "-selection", "clipboard"], value)
        if shutil.which("xsel"):
            return self._pipe(["xsel", "--clipboard", "--input"], value)
        return False

    @staticmethod
    def _pipe(command: list[str], text: str) -> bool:
        try:
            result = subprocess.run(
                command,
                input=text,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                shell=False,
                check=False,
            )
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def _write_windows(text: str) -> bool:
        try:
            import ctypes

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            kernel32.GlobalAlloc.restype = ctypes.c_void_p
            kernel32.GlobalLock.restype = ctypes.c_void_p
            user32.SetClipboardData.restype = ctypes.c_void_p
            cf_unicode_text = 13
            gmem_moveable = 0x0002
            encoded = (text + "\0").encode("utf-16-le")
            if not user32.OpenClipboard(None):
                return False
            handle = None
            try:
                if not user32.EmptyClipboard():
                    return False
                handle = kernel32.GlobalAlloc(gmem_moveable, len(encoded))
                if not handle:
                    return False
                pointer = kernel32.GlobalLock(handle)
                if not pointer:
                    kernel32.GlobalFree(handle)
                    return False
                ctypes.memmove(pointer, encoded, len(encoded))
                kernel32.GlobalUnlock(handle)
                if not user32.SetClipboardData(cf_unicode_text, handle):
                    kernel32.GlobalFree(handle)
                    return False
                handle = None  # the clipboard owns the allocation now
                return True
            finally:
                user32.CloseClipboard()
        except (AttributeError, OSError):
            return False


@dataclass(slots=True)
class PlatformServices:
    clipboard: ClipboardService
    webview_backend: str = "unknown"

    @classmethod
    def detect(cls) -> "PlatformServices":
        # VELA_GUI is an explicit backend selection. When absent we deliberately
        # report unknown rather than guessing from the operating system.
        return cls(
            clipboard=ClipboardService(),
            webview_backend=os.environ.get("VELA_GUI") or "unknown",
        )

    def capabilities(self) -> dict[str, object]:
        return {
            "platform": sys.platform,
            "webview": self.webview_backend,
            "clipboard": self.clipboard.available,
            "filePicker": False,
        }
